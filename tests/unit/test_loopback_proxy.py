from __future__ import annotations

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Iterable, Iterator, List, Tuple

import pytest
import traitlets
from ipywidgets import IntSlider, Widget
from shiny import Session
from shiny.session import session_context
from shinywidgets._dependencies import (
    _LoopbackProxyApp,
    _rewrite_loopback_url,
    localtileserver_layer_proxy,
    mount_loopback_proxy,
)

# --- fakes ---------------------------------------------------------------


class FakeTileLayer(Widget):
    """Stands in for an ipyleaflet layer (localtileserver isn't imported)."""

    url = traitlets.Unicode("").tag(sync=True)


class FakeTileClient:
    """Duck-type of localtileserver.TileClient (server_port/filename/get_tile_url)."""

    def __init__(self, port: int, filename: str) -> None:
        self.server_port = port
        self.filename = filename

    def get_tile_url(self, *, client: bool = False, **kwargs: Any) -> str:
        assert not kwargs
        return (
            f"http://127.0.0.1:{self.server_port}"
            f"/api/tiles/{{z}}/{{x}}/{{y}}.png?filename={self.filename}"
        )


def fake_layer(
    session: Session, port: int, filename: str
) -> Tuple[FakeTileLayer, FakeTileClient]:
    with session_context(session):
        layer = FakeTileLayer()
    client = FakeTileClient(port, filename)
    layer.tile_server = client  # type: ignore[attr-defined]
    layer.url = client.get_tile_url(client=True)
    return layer, client


def proxy_routes(session: Session, port: int) -> List[Any]:
    routes = session.app._dependency_handler.routes  # type: ignore[attr-defined]
    return [r for r in routes if getattr(r, "path", "").rstrip("/") == f"/proxy/{port}"]


# --- ASGI driving ----------------------------------------------------------


def _asgi_request(
    app: Any,
    path: str,
    *,
    method: str = "GET",
    query_string: bytes = b"",
    headers: Iterable[Tuple[bytes, bytes]] = (),
) -> Tuple[int, Dict[bytes, bytes], bytes]:
    """Drive an ASGI app with a single request; return (status, headers, body)."""
    # Mirror the scope starlette's Mount passes to a mounted app: the full
    # path, with the mount prefix moved into root_path
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": "/proxy/1/" + path,
        "raw_path": ("/proxy/1/" + path).encode("latin-1"),
        "root_path": "/proxy/1",
        "query_string": query_string,
        "headers": list(headers),
        "path_params": {},
    }
    messages: List[Dict[str, Any]] = []

    async def receive() -> Dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Dict[str, Any]) -> None:
        messages.append(message)

    asyncio.run(app(scope, receive, send))

    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    resp_headers = {
        k: v
        for m in messages
        if m["type"] == "http.response.start"
        for k, v in m["headers"]
    }
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, resp_headers, body


@pytest.fixture
def upstream_server() -> Iterator[int]:
    """A stub loopback tile server on an ephemeral port; yields the port."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = b"tile-bytes"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        thread.join(timeout=5)


# --- _rewrite_loopback_url ---------------------------------------------------


def test_rewrite_loopback_url() -> None:
    rest = "api/tiles/{z}/{x}/{y}.png?filename=f.tif"
    assert (
        _rewrite_loopback_url(f"http://127.0.0.1:8801/{rest}", 8801)
        == f"proxy/8801/{rest}"
    )
    assert (
        _rewrite_loopback_url(f"http://localhost:8801/{rest}", 8801)
        == f"proxy/8801/{rest}"
    )
    # Root-relative (the old manual recipe) becomes relative, so it also
    # resolves under a path prefix (Connect/shinyapps.io)
    assert _rewrite_loopback_url(f"/proxy/8801/{rest}", 8801) == f"proxy/8801/{rest}"
    # Already relative or unrelated URLs are untouched
    assert _rewrite_loopback_url(f"proxy/8801/{rest}", 8801) == f"proxy/8801/{rest}"
    assert (
        _rewrite_loopback_url("https://tiles.example.com/{z}/{x}/{y}.png", 8801)
        == "https://tiles.example.com/{z}/{x}/{y}.png"
    )
    # A different port's loopback URL is not this proxy's business
    assert (
        _rewrite_loopback_url(f"http://127.0.0.1:9999/{rest}", 8801)
        == f"http://127.0.0.1:9999/{rest}"
    )


# --- mount_loopback_proxy ----------------------------------------------------


def test_mount_is_idempotent_and_unions_filenames(widget_session: Session) -> None:
    app = widget_session.app
    mount_loopback_proxy(app, 8801, allowed_filenames={"a.tif"})
    mount_loopback_proxy(app, 8801, allowed_filenames={"b.tif"})
    routes = proxy_routes(widget_session, 8801)
    assert len(routes) == 1
    proxy = routes[0].app
    assert proxy._allowed_filenames == {"a.tif", "b.tif"}


def test_mount_strengthens_hand_mounted_proxy(widget_session: Session) -> None:
    # The pre-feature recipe mounted an *unguarded* proxy by hand; auto-wiring
    # must add the guard in place, not shadow it (starlette matches the first
    # route, so a second mount would leave the unguarded one in effect)
    app = widget_session.app
    app._dependency_handler.mount(  # type: ignore[attr-defined]
        "/proxy/8801/", _LoopbackProxyApp(8801), name="localtileserver-proxy"
    )
    mount_loopback_proxy(app, 8801, allowed_filenames={"a.tif"})
    routes = proxy_routes(widget_session, 8801)
    assert len(routes) == 1
    assert routes[0].app._allowed_filenames == {"a.tif"}
    # An unguarded mount request never *weakens* an existing guard
    mount_loopback_proxy(app, 8801)
    assert routes[0].app._allowed_filenames == {"a.tif"}


# --- the filename guard ------------------------------------------------------


def test_guard_blocks_unregistered_filenames(upstream_server: int) -> None:
    proxy = _LoopbackProxyApp(upstream_server, allowed_filenames={"ok.tif"})

    status, _, body = _asgi_request(
        proxy, "api/metadata", query_string=b"filename=ok.tif"
    )
    assert status == 200
    assert body == b"tile-bytes"

    status, _, body = _asgi_request(
        proxy, "api/metadata", query_string=b"filename=%2Fetc%2Fpasswd"
    )
    assert status == 403
    assert body == b"Forbidden: unregistered filename"

    # SSRF via /vsicurl/-style remote URLs is blocked too
    status, _, _ = _asgi_request(
        proxy,
        "api/metadata",
        query_string=b"filename=https%3A%2F%2Fevil.example%2Fx.tif",
    )
    assert status == 403

    # Requests without a filename pass (colormap lists, docs, etc.); every
    # file-reading endpoint requires one
    status, _, _ = _asgi_request(proxy, "api/colormaps")
    assert status == 200

    # Any bad value in a repeated parameter is refused
    status, _, _ = _asgi_request(
        proxy, "api/tiles", query_string=b"filename=ok.tif&filename=%2Fetc%2Fpasswd"
    )
    assert status == 403


def test_guard_matches_url_encoded_filenames(upstream_server: int) -> None:
    proxy = _LoopbackProxyApp(
        upstream_server, allowed_filenames={"/tmp/my dir/some file.tif"}
    )
    status, _, _ = _asgi_request(
        proxy,
        "api/tiles",
        query_string=b"filename=%2Ftmp%2Fmy%20dir%2Fsome%20file.tif",
    )
    assert status == 200


def test_no_guard_when_filenames_not_given(upstream_server: int) -> None:
    # The geolibre exposure model: the server tokens its own routes
    proxy = _LoopbackProxyApp(upstream_server)
    status, _, _ = _asgi_request(
        proxy, "api/metadata", query_string=b"filename=%2Fetc%2Fpasswd"
    )
    assert status == 200


# --- localtileserver_layer_proxy ---------------------------------------------


def test_layer_autowire(widget_session: Session) -> None:
    layer, client = fake_layer(widget_session, 8801, "/tmp/ok.tif")

    localtileserver_layer_proxy(layer, widget_session)

    # Proxy mounted with the client's filename registered
    routes = proxy_routes(widget_session, 8801)
    assert len(routes) == 1
    assert routes[0].app._allowed_filenames == {"/tmp/ok.tif"}

    # The layer's loopback URL was rewritten onto the proxy (relative, so it
    # works under a path prefix)
    assert layer.url == ("proxy/8801/api/tiles/{z}/{x}/{y}.png?filename=/tmp/ok.tif")

    # Restyle URLs (client=True) come out proxy-relative in a single step;
    # server-side URLs (client=False) are untouched
    assert client.get_tile_url(client=True).startswith("proxy/8801/")
    assert client.get_tile_url().startswith("http://127.0.0.1:8801/")

    # Wiring again (e.g., a second session) doesn't double-wrap or re-mount
    wrapped = client.get_tile_url
    localtileserver_layer_proxy(layer, widget_session)
    assert client.get_tile_url is wrapped
    assert len(proxy_routes(widget_session, 8801)) == 1


def test_observer_backstop_rewrites_but_never_registers(
    widget_session: Session, upstream_server: int
) -> None:
    layer, _ = fake_layer(widget_session, upstream_server, "/tmp/ok.tif")
    localtileserver_layer_proxy(layer, widget_session)
    proxy = proxy_routes(widget_session, upstream_server)[0].app

    # A direct assignment of a loopback URL (not via get_tile_url) is rewritten
    layer.url = f"http://127.0.0.1:{upstream_server}/api/tiles?filename=/tmp/ok.tif&colormap=magma"
    assert layer.url.startswith(f"proxy/{upstream_server}/")

    # ...but the observed URL's filename is NOT registered: trait values can
    # be pushed by the browser over the comm, so registering from them would
    # let a client poison its own allowlist
    layer.url = f"http://127.0.0.1:{upstream_server}/api/tiles?filename=/etc/passwd"
    assert layer.url.startswith(f"proxy/{upstream_server}/")
    status, _, _ = _asgi_request(
        proxy, "api/tiles", query_string=b"filename=%2Fetc%2Fpasswd"
    )
    assert status == 403

    # Unrelated URLs pass through the observer untouched
    layer.url = "https://tiles.example.com/{z}/{x}/{y}.png"
    assert layer.url == "https://tiles.example.com/{z}/{x}/{y}.png"


def test_noop_for_other_widgets(widget_session: Session) -> None:
    with session_context(widget_session):
        w = IntSlider()
    localtileserver_layer_proxy(w, widget_session)
    routes = widget_session.app._dependency_handler.routes  # type: ignore[attr-defined]
    assert not any(getattr(r, "path", "").startswith("/proxy/") for r in routes)


def test_env_opt_out(widget_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHINYWIDGETS_LOOPBACK_PROXY_DISABLE", "1")
    layer, client = fake_layer(widget_session, 8801, "/tmp/ok.tif")
    url_before = layer.url
    localtileserver_layer_proxy(layer, widget_session)
    assert layer.url == url_before
    assert proxy_routes(widget_session, 8801) == []
    assert client.get_tile_url(client=True).startswith("http://127.0.0.1:8801/")
