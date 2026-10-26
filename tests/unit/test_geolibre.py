from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, List, Tuple

import pytest

pytest.importorskip(
    "geolibre",
    reason="geolibre isn't installed (it requires Python >= 3.11)",
)

from geolibre import Map
from shiny import Session
from shiny.session import session_context
from shinywidgets._dependencies import geolibre_app_mount
from shinywidgets._render_widget_base import set_layout_defaults


def geolibre_map(session: Session, **kwargs: object) -> Map:
    with session_context(session):
        return Map(**kwargs)  # type: ignore[arg-type]


def test_default_height_fills(widget_session: Session) -> None:
    w = geolibre_map(widget_session)
    _, fill = set_layout_defaults(w)
    assert fill is True
    # The embedded app styles its <iframe> from the height trait (once, when
    # it loads), so a filling output sizes the iframe to its container
    assert w.height == "100%"


def test_explicit_widget_height_disables_fill(widget_session: Session) -> None:
    w = geolibre_map(widget_session, height="600px")
    _, fill = set_layout_defaults(w)
    assert fill is False
    assert w.height == "600px"


def test_app_mount_switches_to_remote_mode(widget_session: Session) -> None:
    # shinywidgets serves geolibre's bundled app from the Shiny app itself (so
    # the <iframe> loads same-origin, locally and deployed) and switches the
    # widget to the mode that probes that route
    w = geolibre_map(widget_session)
    geolibre_app_mount(w, widget_session)
    assert w._remote_mode == "remote"
    routes = widget_session.app._dependency_handler.routes  # type: ignore[attr-defined]
    geolibre_mounts = [r for r in routes if getattr(r, "name", None) == "geolibre-app"]
    assert len(geolibre_mounts) == 1
    assert geolibre_mounts[0].path == "/geolibre/app"
    # Mounting again (e.g., a second Map) doesn't duplicate the route
    geolibre_app_mount(geolibre_map(widget_session), widget_session)
    routes = widget_session.app._dependency_handler.routes  # type: ignore[attr-defined]
    assert len([r for r in routes if getattr(r, "name", None) == "geolibre-app"]) == 1


def test_layout_trait_is_geolibres_own(widget_session: Session) -> None:
    # geolibre reuses the `layout` trait name for the app's chrome
    # ("embed"/"full"/"maponly"), shadowing ipywidgets' Layout widget. Make
    # sure set_layout_defaults() doesn't mistake it for a Layout.
    w = geolibre_map(widget_session, layout="maponly")
    assert isinstance(w.layout, str)
    _, fill = set_layout_defaults(w)
    assert fill is True


def _asgi_request(
    app: Any,
    path: str,
    *,
    method: str = "GET",
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
        "query_string": b"",
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


def test_proxy_mount_forwards_to_loopback_server(
    widget_session: Session, tmp_path: Any
) -> None:
    # geolibre serves layers backed by files on the server's disk (e.g.,
    # add_cog() of a local GeoTIFF) from its loopback server, which a remote
    # browser can't reach. shinywidgets mounts a reverse proxy at
    # /proxy/{port}/ so they work same-origin (deployed included), the same
    # way jupyter-server-proxy does for Jupyter servers.
    w = geolibre_map(widget_session)
    geolibre_app_mount(w, widget_session)
    port = w._app_port
    assert port > 0
    routes = widget_session.app._dependency_handler.routes  # type: ignore[attr-defined]
    proxies = [
        r for r in routes if getattr(r, "name", None) == f"geolibre-proxy-{port}"
    ]
    assert len(proxies) == 1
    assert proxies[0].path == f"/proxy/{port}"
    # Mounting again (e.g., a second Map) doesn't duplicate the route
    geolibre_app_mount(geolibre_map(widget_session), widget_session)
    routes = widget_session.app._dependency_handler.routes  # type: ignore[attr-defined]
    assert (
        len([r for r in routes if getattr(r, "name", None) == f"geolibre-proxy-{port}"])
        == 1
    )

    proxy = proxies[0].app

    # Register a local file with geolibre's loopback server, then fetch it
    # through the proxy
    from geolibre._server import register_local_file

    f = tmp_path / "data.txt"
    f.write_bytes(b"0123456789")
    rel = register_local_file(f).split(f":{port}/", 1)[1]
    assert rel.startswith("_geolibre_local/")

    status, _, body = _asgi_request(proxy, rel)
    assert status == 200
    assert body == b"0123456789"

    # Range requests pass through (geolibre's GeoTIFF reader depends on them)
    status, headers, body = _asgi_request(
        proxy, rel, headers=[(b"range", b"bytes=2-5")]
    )
    assert status == 206
    assert body == b"2345"
    assert headers.get(b"content-range") == b"bytes 2-5/10"

    # HEAD works (the front-end's reachability probe uses it), and hits the
    # loopback server (i.e., the app bundle, not shinywidgets' own files)
    status, _, body = _asgi_request(proxy, "index.html", method="HEAD")
    assert status == 200
    assert body == b""

    # Missing files 404; unsupported methods 405
    status, _, _ = _asgi_request(proxy, "_geolibre_local/nope/nope.txt")
    assert status == 404
    status, _, _ = _asgi_request(proxy, "index.html", method="POST")
    assert status == 405
