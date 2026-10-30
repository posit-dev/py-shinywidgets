from __future__ import annotations

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Iterable, Iterator, List, Tuple

import pytest
import shinywidgets._shinywidgets as sw
import traitlets
from ipywidgets import IntSlider, Widget
from shiny import App, Inputs, Outputs, Session, ui
from shiny._connection import MockConnection
from shiny.session import session_context
from shinywidgets import shared_lifetime
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

    # Mirrors localtileserver 1.0.0's signature, in which `client` may be
    # passed positionally (6th parameter)
    def get_tile_url(
        self,
        indexes: Any = None,
        colormap: Any = None,
        vmin: Any = None,
        vmax: Any = None,
        nodata: Any = None,
        client: bool = False,
    ) -> str:
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


def only_token(proxy: _LoopbackProxyApp) -> str:
    assert len(proxy._capabilities) == 1
    return next(iter(proxy._capabilities))


def _noop_server(input: Inputs, output: Outputs, session: Session) -> None:
    pass


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
    # (percent-decoded) path, with the mount prefix moved into root_path
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
    """A stub loopback tile server on an ephemeral port; yields the port.

    Echoes the raw request target it received, so tests can assert exactly
    what the proxy forwarded."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = self.path.encode("latin-1")
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
    first = mount_loopback_proxy(app, 8801, allowed_filenames={"a.tif"})
    second = mount_loopback_proxy(app, 8801, allowed_filenames={"b.tif"})
    routes = proxy_routes(widget_session, 8801)
    assert len(routes) == 1
    assert first is second is routes[0].app
    assert first is not None and first._allowed_filenames == {"a.tif", "b.tif"}


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
    # ...but an empty iterable still strengthens an unguarded mount to guarded
    app._dependency_handler.mount(  # type: ignore[attr-defined]
        "/proxy/8802/", _LoopbackProxyApp(8802), name="localtileserver-proxy-2"
    )
    mount_loopback_proxy(app, 8802, allowed_filenames=())
    assert proxy_routes(widget_session, 8802)[0].app._allowed_filenames == set()


# --- the raster-source guard -------------------------------------------------


def test_guard_blocks_unregistered_filenames(upstream_server: int) -> None:
    proxy = _LoopbackProxyApp(upstream_server, allowed_filenames={"ok.tif"})

    status, _, body = _asgi_request(
        proxy, "api/metadata", query_string=b"filename=ok.tif"
    )
    assert status == 200
    assert body == b"/api/metadata?filename=ok.tif"

    status, _, body = _asgi_request(
        proxy, "api/metadata", query_string=b"filename=%2Fetc%2Fpasswd"
    )
    assert status == 403
    assert body == b"Forbidden: unregistered raster source"

    # SSRF via /vsicurl/-style remote URLs is blocked too
    status, _, _ = _asgi_request(
        proxy,
        "api/metadata",
        query_string=b"filename=https%3A%2F%2Fevil.example%2Fx.tif",
    )
    assert status == 403

    # Requests without a source selector pass (colormap lists, docs, etc.);
    # every file-reading endpoint requires one
    status, _, _ = _asgi_request(proxy, "api/colormaps")
    assert status == 200

    # Any bad value in a repeated parameter is refused
    status, _, _ = _asgi_request(
        proxy, "api/tiles", query_string=b"filename=ok.tif&filename=%2Fetc%2Fpasswd"
    )
    assert status == 403


def test_guard_covers_every_source_selector(upstream_server: int) -> None:
    # localtileserver 1.0.0 also reads rasters from `files` (comma-separated,
    # mosaic endpoints), `url` (server-side-fetched STAC URL, i.e. SSRF), and
    # `filenameA`/`filenameB` (the /split/ viewer in web/fastapi_app.py);
    # a filename-only guard would leave those wide open
    proxy = _LoopbackProxyApp(upstream_server, allowed_filenames={"a.tif", "b.tif"})

    status, _, _ = _asgi_request(
        proxy, "api/mosaic/tiles/0/0/0.png", query_string=b"files=a.tif,b.tif"
    )
    assert status == 200

    status, _, _ = _asgi_request(
        proxy,
        "api/mosaic/tiles/0/0/0.png",
        query_string=b"files=a.tif,%2Fetc%2Fpasswd",
    )
    assert status == 403

    status, _, _ = _asgi_request(
        proxy,
        "api/stac/info",
        query_string=b"url=https%3A%2F%2Fevil.example%2Fitem.json",
    )
    assert status == 403

    # The /split/ viewer's filenameA/filenameB
    status, _, _ = _asgi_request(proxy, "split/", query_string=b"filenameA=a.tif")
    assert status == 200
    status, _, _ = _asgi_request(
        proxy, "split/", query_string=b"filenameA=a.tif&filenameB=%2Fetc%2Fpasswd"
    )
    assert status == 403
    status, _, _ = _asgi_request(
        proxy, "split/", query_string=b"filenameA=http%3A%2F%2Fevil.example%2Fx.tif"
    )
    assert status == 403


def test_guard_blocks_xarray_routes(upstream_server: int) -> None:
    # /api/xarray/* reads datasets from a server-side in-memory registry (and
    # implicitly selects a sole registered dataset) with no checked selector,
    # so there is nothing to authorize against; guarded proxies refuse the
    # whole prefix until per-dataset authorization exists. Unguarded proxies
    # (geolibre's model) forward them.
    guarded = _LoopbackProxyApp(upstream_server, allowed_filenames=set())
    for path in ("api/xarray/info", "api/xarray/tiles/0/0/0.png"):
        status, _, _ = _asgi_request(guarded, path)
        assert status == 403
    unguarded = _LoopbackProxyApp(upstream_server)
    status, _, _ = _asgi_request(unguarded, "api/xarray/info")
    assert status == 200


def test_guard_escaped_question_mark_cannot_smuggle_query(
    upstream_server: int,
) -> None:
    # A request to /proxy/{port}/api/metadata%3Ffilename=... reaches the proxy
    # with the (decoded) `?` in scope["path"] and an empty query string, so
    # the guard sees no selector; forwarding the decoded path verbatim would
    # turn it back into a query string upstream, bypassing the guard
    proxy = _LoopbackProxyApp(upstream_server, allowed_filenames={"ok.tif"})
    status, _, body = _asgi_request(proxy, "api/metadata?filename=/etc/passwd")
    assert status == 200  # nothing to guard against in the real query string
    # ...but the upstream receives an opaque encoded path, not a smuggled query
    assert body.startswith(b"/api/metadata%3Ffilename%3D")
    assert b"?" not in body


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


# --- capability tokens --------------------------------------------------------


def test_capability_tokens_authorize_exactly_their_files(
    upstream_server: int,
) -> None:
    proxy = _LoopbackProxyApp(upstream_server, allowed_filenames=set())
    token_a = proxy.register_filenames(["/home/alice/private.tif"])
    token_b = proxy.register_filenames(["/home/bob/private.tif"])
    # Re-registering the same set reuses the token
    assert proxy.register_filenames(["/home/alice/private.tif"]) == token_a

    def req(query: bytes) -> int:
        status, _, _ = _asgi_request(proxy, "api/tiles", query_string=query)
        return status

    # A valid token reads exactly its own file...
    assert req(b"filename=/home/alice/private.tif&sw_token=" + token_a.encode()) == 200
    # ...and nothing else
    assert req(b"filename=/home/bob/private.tif&sw_token=" + token_a.encode()) == 403
    # Knowing or guessing a path (or the other session's path) is not enough
    assert req(b"filename=/home/alice/private.tif") == 403
    assert req(b"filename=%2Fetc%2Fpasswd&sw_token=" + token_a.encode()) == 403
    # Unknown tokens authorize nothing
    assert req(b"filename=/home/bob/private.tif&sw_token=forged") == 403
    assert req(b"filename=/home/bob/private.tif&sw_token=" + token_b.encode()) == 200


def test_capability_can_be_registered_in_another_proxy(upstream_server: int) -> None:
    # A client shared across multiple Shiny Apps gets one stable token,
    # registered in each App's proxy (see test_stable_token_across_apps)
    other = _LoopbackProxyApp(upstream_server, allowed_filenames=set())
    proxy = _LoopbackProxyApp(upstream_server, allowed_filenames=set())
    token = proxy.register_filenames(["/tmp/x.tif"])
    assert other.register_filenames(["/tmp/x.tif"], token=token) == token
    status, _, _ = _asgi_request(
        other,
        "api/tiles",
        query_string=b"filename=/tmp/x.tif&sw_token=" + token.encode(),
    )
    assert status == 200


# --- localtileserver_layer_proxy ---------------------------------------------


def test_layer_autowire(widget_session: Session, upstream_server: int) -> None:
    layer, client = fake_layer(widget_session, upstream_server, "/tmp/ok.tif")

    localtileserver_layer_proxy(layer, widget_session)

    # Proxy mounted, guarded; the filename is registered behind a capability
    # token (not the app-wide plain allowlist)
    routes = proxy_routes(widget_session, upstream_server)
    assert len(routes) == 1
    proxy = routes[0].app
    assert proxy._allowed_filenames == set()
    token = only_token(proxy)
    assert proxy.authorized_filenames(token) == frozenset({"/tmp/ok.tif"})

    # The layer's loopback URL was rewritten onto the proxy (relative, so it
    # works under a path prefix), with the capability token attached
    assert layer.url == (
        f"proxy/{upstream_server}/api/tiles/{{z}}/{{x}}/{{y}}.png"
        f"?filename=/tmp/ok.tif&sw_token={token}"
    )

    # Restyle URLs (client=True) come out proxy-relative in a single step,
    # whether `client` is passed by keyword or positionally; server-side URLs
    # (client=False, the default) are untouched
    for restyle_url in (
        client.get_tile_url(client=True),
        client.get_tile_url(None, None, None, None, None, True),
    ):
        assert restyle_url.startswith(f"proxy/{upstream_server}/")
        assert f"sw_token={token}" in restyle_url
    assert client.get_tile_url().startswith(f"http://127.0.0.1:{upstream_server}/")

    # The rewritten URL is servable: token + registered filename passes the
    # guard; the same request without the token is refused
    status, _, _ = _asgi_request(
        proxy,
        "api/tiles/0/0/0.png",
        query_string=f"filename=/tmp/ok.tif&sw_token={token}".encode(),
    )
    assert status == 200
    status, _, _ = _asgi_request(
        proxy, "api/tiles/0/0/0.png", query_string=b"filename=/tmp/ok.tif"
    )
    assert status == 403

    # Wiring again (e.g., a second session) doesn't double-wrap or re-mount
    url_after_first_wire = layer.url
    wrapped = client.get_tile_url
    localtileserver_layer_proxy(layer, widget_session)
    assert client.get_tile_url is wrapped
    assert len(proxy_routes(widget_session, upstream_server)) == 1
    # ...and doesn't append a second token (shared layers are re-wired once
    # per session; the URL must not grow each time)
    assert layer.url == url_after_first_wire
    assert layer.url.count("sw_token=") == 1


def test_token_never_attached_to_external_urls(
    widget_session: Session, upstream_server: int
) -> None:
    # A layer whose URL is unrelated to the loopback server keeps it
    # untouched: attaching the capability token would send the credential to
    # an external server
    layer, client = fake_layer(widget_session, upstream_server, "/tmp/ok.tif")
    external = "https://tiles.example.com/{z}/{x}/{y}.png"
    layer.url = external
    localtileserver_layer_proxy(layer, widget_session)
    assert layer.url == external
    # The proxy is still mounted and the wrapper still only rewrites loopback
    # URLs
    assert len(proxy_routes(widget_session, upstream_server)) == 1
    assert client.get_tile_url().startswith(f"http://127.0.0.1:{upstream_server}/")


def test_stable_token_across_apps(
    widget_session: Session, upstream_server: int
) -> None:
    # A client (or shared layer) reused in a second Shiny App gets the SAME
    # capability token registered in that App's proxy, so URLs minted for the
    # first App are accepted by the second's
    layer, client = fake_layer(widget_session, upstream_server, "/tmp/ok.tif")
    localtileserver_layer_proxy(layer, widget_session)
    token = only_token(proxy_routes(widget_session, upstream_server)[0].app)

    app2 = App(ui.page_fluid(), _noop_server)
    session2 = app2._create_session(MockConnection())
    try:
        localtileserver_layer_proxy(layer, session2)
        proxy2 = proxy_routes(session2, upstream_server)[0].app
        assert proxy2.authorized_filenames(token) == frozenset({"/tmp/ok.tif"})
        # and the layer URL still carries that one token (no duplicates)
        assert layer.url.count("sw_token=") == 1
        assert f"sw_token={token}" in layer.url
    finally:
        asyncio.run(session2.close())


def test_observer_backstop_rewrites_and_reuses_only_existing_tokens(
    widget_session: Session, upstream_server: int
) -> None:
    layer, _ = fake_layer(widget_session, upstream_server, "/tmp/ok.tif")
    localtileserver_layer_proxy(layer, widget_session)
    proxy = proxy_routes(widget_session, upstream_server)[0].app
    token = only_token(proxy)

    # A direct assignment of a loopback URL (not via get_tile_url) is
    # rewritten; since its filename was registered at wire-up, the existing
    # token is re-attached (the browser already holds it, so this grants it
    # nothing new)
    layer.url = f"http://127.0.0.1:{upstream_server}/api/tiles?filename=/tmp/ok.tif&colormap=magma"
    assert layer.url.startswith(f"proxy/{upstream_server}/")
    assert f"sw_token={token}" in layer.url

    # ...but an unregistered filename is rewritten WITHOUT a token and never
    # registered: trait values can be pushed by the browser over the comm, so
    # registering from them would let a client poison its own allowlist. The
    # proxy refuses it (403) -- loudly, rather than leaking
    layer.url = f"http://127.0.0.1:{upstream_server}/api/tiles?filename=/etc/passwd"
    assert layer.url.startswith(f"proxy/{upstream_server}/")
    assert "sw_token" not in layer.url
    status, _, _ = _asgi_request(
        proxy, "api/tiles", query_string=b"filename=%2Fetc%2Fpasswd"
    )
    assert status == 403

    # Unrelated URLs pass through the observer untouched
    layer.url = "https://tiles.example.com/{z}/{x}/{y}.png"
    assert layer.url == "https://tiles.example.com/{z}/{x}/{y}.png"


def test_shared_widget_layer_is_wired_on_open(
    widget_session: Session, shared_state: None, upstream_server: int
) -> None:
    # Layers constructed in shared_lifetime() never open a ShinyComm, so the
    # comm-open hook never fires for them; open_shared_in() must wire them
    # before serializing their state, or deployed shared maps keep loopback
    # URLs
    with shared_lifetime():
        layer = FakeTileLayer()
    client = FakeTileClient(upstream_server, "/tmp/shared.tif")
    layer.tile_server = client  # type: ignore[attr-defined]
    layer.url = client.get_tile_url(client=True)

    sw.open_shared_in(layer, widget_session)

    assert layer.url.startswith(f"proxy/{upstream_server}/")
    proxy = proxy_routes(widget_session, upstream_server)[0].app
    token = only_token(proxy)
    assert proxy.authorized_filenames(token) == frozenset({"/tmp/shared.tif"})
    assert f"sw_token={token}" in layer.url


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
