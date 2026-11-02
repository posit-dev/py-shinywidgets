import asyncio
import http.client
import importlib
import inspect
import json
import os
import re
import secrets
import tempfile
import threading
import warnings
from types import ModuleType
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, quote

import packaging.version
from htmltools import HTMLDependency, tags
from htmltools._core import (
    HTMLDependencySource,  # pyright: ignore[reportPrivateImportUsage]
)
from ipywidgets.widgets.domwidget import DOMWidget
from ipywidgets.widgets.widget import Widget
from jupyter_core.paths import jupyter_path
from shiny import App, Session
from starlette.types import Receive, Scope, Send

try:
    from starlette._utils import get_route_path  # starlette >= 0.47
except ImportError:  # pragma: no cover
    from starlette.routing import get_route_path  # pyright: ignore[reportPrivateImportUsage]

from . import __version__
from ._utils import package_dir


# TODO: scripts/static_download.R should produce/update these
def output_binding_dependency() -> HTMLDependency:
    # Jupyter Notebook/Lab both come "preloaded" with several @jupyter-widgets packages
    # (i.e., base, controls, output), all of which are bundled into this extension.js file
    # provided by the widgetsnbextension package, which is a dependency of ipywidgets.
    # https://github.com/nteract/nes/tree/master/portable-widgets
    # https://github.com/jupyter-widgets/ipywidgets/blob/88cec8/packages/html-manager/src/htmlmanager.ts#L115-L120
    #
    # Unfortunately, I don't think there is a good way for us to "pre-bundle" these dependencies
    # since they could change depending on the version of ipywidgets (and ipywidgets itself
    # doesn't include these dependencies in such a way that require("@jupyter-widget/base") would
    # work robustly when used in other 3rd party widgets). Moreover, I don't think we can simply
    # have @jupyter-widget/base point to https://unpkg.com/@jupyter-widgets/base@__version__/lib/index.js
    # (or a local version of this) since it appears the lib entry points aren't usable in the browser.
    #
    # All this is to say that I think we are stuck with this mega 3.5MB file that contains all of the
    # stuff we need to render widgets outside of the notebook.
    return HTMLDependency(
        name="ipywidget-output-binding",
        version=__version__,
        source={"package": "shinywidgets", "subdir": "static"},
        script=[
            # require-config.js must load before libembed-amd.js so require.js
            # resolves the @jupyter-widgets/* AMD module URLs to this directory
            # (the widgets bundles derive their CSS font URLs from it).
            {"src": "require-config.js"},
            {"src": "libembed-amd.js"},
            # Bundle our output.js in the same dependency as libembded since Quarto
            # has a bug where it doesn't renders dependencies in the order they are defined
            # (i.e., this way we can ensure the output.js script always comes after the libembed-amd.js script tag)
            {"src": "output.js"},
        ],
        stylesheet={"href": "shinywidgets.css"},
    )


def custom_elements_dependency() -> HTMLDependency:
    # Perspective's anywidget ES module calls customElements.define() at module
    # scope, and anywidget evaluates that module once per model, so a second model
    # in the page (e.g., after a re-render) throws "the name ... has already been
    # used" and never initializes. Perspective guards its own registrations
    # against this, but these three elements (registered at module scope by its
    # bundled regular-layout dependency) are unguarded. Ignoring just their
    # redefinition leaves the elements registered by the first evaluation in
    # place, while duplicate registration of any other element still throws, as
    # the platform intends.
    return HTMLDependency(
        name="shinywidgets-custom-elements",
        version=__version__,
        head=tags.script(
            """
(function () {
  const PERSPECTIVE_ELEMENTS = new Set([
    "regular-layout",
    "regular-layout-frame",
    "regular-layout-tab",
  ]);
  const define = customElements.define;
  customElements.define = function (name, constructor, options) {
    if (PERSPECTIVE_ELEMENTS.has(name) && customElements.get(name)) return;
    define.call(customElements, name, constructor, options);
  };
})();
"""
        ),
    )


def reactable_dependency() -> HTMLDependency:
    """
    The reactable stylesheet (reactable-py's widget JS is loaded as an ipyreact
    module, but its CSS isn't part of that bundle: Jupyter users are expected to
    call ``reactable.embed_css()`` themselves, which has no effect in Shiny).
    """
    from importlib.metadata import version as package_version

    return HTMLDependency(
        name="reactable",
        version=package_version("reactable"),
        source=HTMLDependencySource(
            subdir=os.path.join(package_dir("reactable"), "static")
        ),
        stylesheet={"href": "reactable-py.esm.css"},
    )


# TODO: this function might have to be recursive since it's technically
# possible for a Widget to have traits that are themselves Widgets
# (which could have their own npm module), but in practice, I haven't seen any cases
# where a 3rd party widget can contain a 3rd party widget.
def require_dependencies(
    w: Widget, session: Session, warn_if_missing: bool = True
) -> List[HTMLDependency]:
    """
    Obtain HTMLDependencies for a 3rd party ipywidget that point
    require('widget-npm-package') requests in the browser to the correct local
    paths. The first entry serves the widget's own module; any additional
    entries serve AMD externals of the widget's bundle that are themselves
    installed nbextensions (see amd_require_config()).
    """

    # The relevant npm package should be specified as an attribute on the widget
    # instance. If the widget is installed as a jupyter extension, in most cases, that
    # name will registered at the extension name/directory
    # (ipyvue's ForceLoad is a DOMWidget with `_view_module = None`, so fall through
    # to `_model_module` when the view module is unset)
    module_attrs = ["_model_module"]
    if isinstance(w, DOMWidget):
        module_attrs.insert(0, "_view_module")
    module_name: str = next(
        (name for attr in module_attrs if (name := getattr(w, attr, None))),
        widget_pkg(w),
    )

    # ipywidgets (i.e., @jupyter-widgets) come pre-bundled in libembed-amd.js
    # # (i.e., _core() dependencies)
    if module_name.startswith("@jupyter-widgets/"):
        return []

    # It's technically possible for the npm package name to be different from the actual
    # extension path (defined by `_jupyter_nbextension_paths` in __init__.py), but we
    # also don't have a fool-proof way to discovering the relevant __init__.py file,
    # which is why we only use look for it if the npm package isn't installed
    module_dir = jupyter_extension_path(module_name)
    if module_dir is None:
        module_dir = jupyter_extension_path(jupyter_extension_destination(w))
        if module_dir is None:
            if warn_if_missing:
                warnings.warn(
                    f"Couldn't find local path to widget extension for {type(w)}."
                    + " Since a CDN fallback is provided, the widget will still render if an internet connection is available."
                    + " To avoid depending on a CDN, make sure the widget is installed as a jupyter extension.",
                    stacklevel=2,
                )
            return []

    if module_name == "anywidget":
        module_dir = relax_anywidget_init_timeout(module_dir)

    version = parse_version_safely(getattr(w, "_model_module_version", "1.0"))

    deps: List[HTMLDependency] = []
    # The widget's own module, plus any AMD externals (of the modules visited
    # along the way) that are themselves installed nbextensions
    seen: set[str] = set()
    worklist = [(module_name, module_dir, version)]
    while worklist:
        name, dir_, ver = worklist.pop(0)
        if name in seen:
            continue
        seen.add(name)
        source = HTMLDependencySource(subdir=dir_)
        dep = HTMLDependency(name, ver, source=source)
        # Get the location where the dependency files will be mounted by the shiny app
        # and use that to inform the requirejs import path
        href = dep.source_path_map(lib_prefix=session.app.lib_prefix)["href"]
        config, nbextensions = amd_require_config(name, dir_, href)
        # Basically our equivalent of the extension.js file provided by the cookiecutter
        # https://github.com/jupyter-widgets/widget-cookiecutter/blob/master/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js
        deps.append(
            HTMLDependency(
                name,
                ver,
                source=source,
                all_files=True,
                head=tags.script(f"window.require.config({json.dumps(config)})"),
            )
        )
        for ext in nbextensions:
            ext_dir = jupyter_extension_path(ext)
            if ext_dir is not None:
                worklist.append((ext, ext_dir, dir_version(ext_dir)))

    return deps


# Module names that a widget bundle may declare in the define([...]) header of
# its AMD bundle, but that shinywidgets' browser environment already provides:
# the @jupyter-widgets packages come prebundled in libembed-amd.js, and the
# rest are require.js or classic-notebook builtins
AMD_PREBUNDLED = {
    "module",
    "require",
    "exports",
    "jquery",
    "jupyter-js-widgets",
}


def amd_externals(module_dir: str) -> List[str]:
    """
    The externals declared by an nbextension's AMD bundle (in the define([...])
    header of its index.js) that shinywidgets' browser environment doesn't
    already provide.

    Widget packages built with a webpack `externals` config (e.g., ipyvolume
    and pythreejs externalize `three`; jupyter-vuetify externalizes
    `jupyter-vue`) rely on the classic notebook's global require.config
    registry (built up at page load from every enabled nbextension's
    extension.js) to resolve those names. shinywidgets loads widget modules on
    demand instead, so without an explicit paths/map entry, require.js
    resolves such names relative to the app root (404).
    """
    try:
        with open(
            os.path.join(module_dir, "index.js"), encoding="utf-8", errors="replace"
        ) as f:
            head = f.read(8192)
    except OSError:
        return []
    m = re.search(r"define\(\s*\[([^\]]*)\]", head)
    if not m:
        # Not an AMD bundle (e.g., an anywidget ESM index.js), or not one we
        # can parse; either way there's nothing to resolve
        return []
    deps = re.findall(r"""["']([^"']+)["']""", m.group(1))
    return [
        dep
        for dep in deps
        if dep not in AMD_PREBUNDLED
        and not dep.startswith(("@jupyter-widgets/", "base/js/", "./", "../"))
    ]


def amd_require_config(
    module_name: str, module_dir: str, href: str
) -> "tuple[dict[str, object], List[str]]":
    """
    The require.js config for one nbextension module: a paths entry for the
    module itself, plus scoped aliases for any externals the bundle ships
    inside its own nbextension directory. Also returns the names of externals
    that are themselves installed nbextensions (they need their own dependency
    to mount and configure them).
    """
    paths: Dict[str, str] = {module_name: os.path.join(href, "index")}
    map_: Dict[str, Dict[str, str]] = {}
    shim: Dict[str, Dict[str, str]] = {}
    nbextensions: List[str] = []
    for ext in amd_externals(module_dir):
        ext_file = os.path.join(module_dir, f"{ext}.js")
        if os.path.isfile(ext_file):
            # The bundle ships its own copy of the external: serve it under an
            # alias scoped to this module (via require.js map) -- another
            # module may ship an incompatible build under the same name
            # (ipyvolume and pythreejs, for example, bundle different
            # three.js builds, and an ipyvolume figure needs both)
            alias = f"{module_name}/{ext}"
            paths[alias] = os.path.join(href, ext)
            map_[module_name] = {**map_.get(module_name, {}), ext: alias}
            global_name = umd_global(ext_file)
            if global_name is not None:
                # UMD bundles take the global-export branch (shiny's require.js
                # wrapper keeps define.amd = false), so expose the global as
                # the module value
                shim[alias] = {"exports": global_name}
        elif jupyter_extension_path(ext) is not None:
            nbextensions.append(ext)
        # Otherwise leave the external unresolved. The widget-level CDN retry
        # does not configure paths for its bare externals.
    config: dict[str, object] = {"paths": paths}
    if map_:
        config["map"] = map_
    if shim:
        config["shim"] = shim
    return config, nbextensions


def umd_global(js_file: str) -> Optional[str]:
    """
    The global variable a UMD-style bundle exports, or None for a plain AMD
    bundle (which provides its module value by calling define()).
    """
    try:
        with open(js_file, encoding="utf-8", errors="replace") as f:
            head = f.read(1024)
    except OSError:
        return None
    # Skip past leading comments/whitespace
    stripped = re.sub(r"\A(?:\s|/\*.*?\*/|//[^\n]*)*", "", head, flags=re.S)
    if stripped.startswith("define("):
        return None
    # The UMD global-export branch: rollup writes `global.Name = {}`, webpack
    # writes `root["Name"] = ...`
    m = re.search(r"\.([A-Za-z_$][\w$]*)\s*=\s*\{\s*\}", head) or re.search(
        r"""\[["']([A-Za-z_$][\w$]*)["']\]\s*=""", head
    )
    if m is None:
        warnings.warn(
            f"{js_file} doesn't look like an AMD bundle, but the global it "
            "exports couldn't be determined; it will be served without a "
            "require.js shim, which may prevent the widget from rendering.",
            stacklevel=2,
        )
        return None
    return m.group(1)


def dir_version(module_dir: str) -> str:
    """
    A pseudo-version for an nbextension we have no widget instance to take a
    module version from (e.g., an AMD external of a widget's bundle): use the
    newest file mtime so a reinstall/upgrade still busts the lib cache.
    """
    try:
        mtime = max(
            os.path.getmtime(os.path.join(module_dir, f))
            for f in os.listdir(module_dir)
        )
        return f"0.0.{int(mtime)}"
    except (OSError, ValueError):
        return "0.0"


def geolibre_app_mount(w: Widget, session: Session) -> None:
    """
    Serve geolibre's bundled app from the Shiny app and use it for the widget's
    <iframe> (works locally *and* deployed).

    geolibre's widget renders the full GeoLibre SPA in an <iframe>. By default
    the app is served by a localhost server in the Python process, which a
    remote browser (i.e., any deployed app) can't reach. For remote Jupyter
    servers, geolibre's front-end instead probes two same-origin routes, in
    order: `{base_url}proxy/{port}/` (the jupyter-server-proxy route to the
    kernel's localhost server) and `{base_url}geolibre/app/` (its Jupyter
    Server extension route). Mount *both* equivalents on the Shiny app and
    switch the widget to its "remote" mode, so the first probe finds the
    proxy mount. (geolibre reads `base_url` from the page's
    jupyter-config-data element, defaulting to "/"; js/src/output.ts injects
    one so the routes also resolve when the app is served under a path
    prefix.)

    The proxy mount is the important one: only when the app loads through
    `{base_url}proxy/{port}/` does geolibre's front-end rewrite the loopback
    URLs of layers backed by files on the server's disk (e.g., `add_cog()` of
    a local GeoTIFF) onto that same-origin base -- so it's what makes such
    layers work in deployed apps, not just for same-host browsers. The
    extension-style mount stays as a fallback (e.g., if the localhost server
    isn't running).
    """
    handler = session.app._dependency_handler

    # Mount once per App (init_shiny_widget() runs for every widget)
    for route in handler.routes:
        if getattr(route, "name", None) == "geolibre-app":
            break
    else:
        from starlette.staticfiles import StaticFiles

        app_dir = os.path.join(package_dir("geolibre"), "static", "app")
        if os.path.isdir(app_dir):
            handler.mount(
                "/geolibre/app/",
                StaticFiles(directory=app_dir),
                name="geolibre-app",
            )

    port = int(getattr(w, "_app_port", 0) or 0)
    if port > 0:
        for route in handler.routes:
            if getattr(route, "name", None) == f"geolibre-proxy-{port}":
                break
        else:
            handler.mount(
                f"/proxy/{port}/",
                _LoopbackProxyApp(port),
                name=f"geolibre-proxy-{port}",
            )

    # Remote mode probes the mounts above (and ignores the localhost
    # `_app_url`). The localhost server keeps running either way; the proxy
    # mount forwards to it.
    w._remote_mode = "remote"  # type: ignore[attr-defined]


# Hop-by-hop headers (plus Host/Accept-Encoding, which http.client manages
# itself) that the loopback proxy must not forward in either direction.
# Query parameters localtileserver 1.0.0 endpoints read raster sources from:
# `filename` (tiles/metadata/... and the `/` viewer), `files`
# (comma-separated, mosaic endpoints), `url` (server-side-fetched STAC URL,
# i.e. an SSRF vector), and `filenameA`/`filenameB` (the `/split/` viewer in
# web/fastapi_app.py). Guarded proxies refuse requests whose values aren't
# authorized.
_LOOPBACK_PROXY_SOURCE_PARAMS = ("filename", "url", "filenameA", "filenameB")

# The xarray endpoints read datasets from a server-side in-memory registry
# (with implicit selection of a sole dataset) rather than from a checked
# selector. Nothing in localtileserver 1.0.0 populates that registry (it's a
# manual extension point), and there is no per-dataset authorization to key
# off, so guarded proxies refuse the whole prefix until one exists.
_LOOPBACK_PROXY_BLOCKED_PREFIX = "/api/xarray/"

# Raster-reading route prefixes in localtileserver 1.0.0 (web/routers/*.py)
# mapped to the source selector each actually consumes. A request that lacks
# the route's own selector falls back *upstream* to a default source — the
# public SF Bay sample dataset, or `app.state.mosaic_assets` (another
# session's registered mosaic) — even when it carries some *other* selector
# the endpoint ignores, so on guarded proxies these routes require an
# authorized value of their own selector. Selector-free access is only safe
# on the remaining routes (palette/colormap lists, docs, viewer HTML), which
# read no rasters.
_LOOPBACK_PROXY_ROUTE_SELECTORS = (
    ("/api/mosaic/", ("files",)),
    ("/api/stac/", ("url",)),
    ("/api/tiles/", ("filename",)),
    ("/api/metadata", ("filename",)),
    ("/api/bounds", ("filename",)),
    ("/api/validate", ("filename",)),
    ("/api/statistics", ("filename",)),
    ("/api/thumbnail.", ("filename",)),
    ("/api/part.", ("filename",)),
    ("/api/feature.", ("filename",)),
)

# Query parameter carrying a `_LoopbackProxyApp` capability token
_LOOPBACK_PROXY_TOKEN_PARAM = "sw_token"

_LOOPBACK_PROXY_DROP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "host",
        "accept-encoding",
    }
)


class _LoopbackProxyAborted(Exception):
    pass


class _LoopbackProxyApp:
    """
    A minimal ASGI reverse proxy that forwards HTTP requests to a server bound
    to 127.0.0.1:{port} in this process.

    geolibre's bundled static server serves the app bundle and tokenized
    local-file/tile routes from loopback, which a remote browser can't reach.
    Mounted at `/proxy/{port}/` (see geolibre_app_mount()), this plays the
    role of jupyter-server-proxy for the Shiny app. Note it makes the
    loopback server reachable by anyone who can reach the Shiny app; the
    local-file routes are protected by unguessable per-process tokens (the
    same exposure model as jupyter-server-proxy).

    Only GET/HEAD/OPTIONS are forwarded (all the server implements). The
    blocking http.client I/O runs on a thread, streaming the response through
    a bounded queue so large files don't have to be buffered whole (geolibre's
    server answers range requests, so chunks stay small).
    """

    _CHUNK_SIZE = 65536

    def __init__(self, port: int, allowed_filenames: Optional[set[str]] = None) -> None:
        """
        `allowed_filenames`: when a set is given, any request carrying a
        raster-source query parameter (`filename`, `files` — comma-separated —
        `url`, `filenameA`/`filenameB`: the selectors localtileserver 1.0.0's
        endpoints read files from) whose value is not authorized is refused
        with a 403, as is any request under `/api/xarray/` (see
        `_LOOPBACK_PROXY_BLOCKED_PREFIX`). A value is
        authorized if it is in the (app-wide) set, or if the request's
        `sw_token` parameter is a capability token registered for it via
        `register_filenames()` — the per-registration alternative to the
        app-wide set, so one session's users can't read another session's
        rasters by knowing or guessing their paths. Requests without any
        selector parameter pass (every file-reading endpoint requires one).
        `None` (the default) forwards everything, the right model for servers
        that token their own file routes (geolibre) — the same exposure model
        as jupyter-server-proxy.
        """
        self._port = port
        self._allowed_filenames = allowed_filenames
        # capability token -> the filenames that token authorizes
        self._capabilities: Dict[str, FrozenSet[str]] = {}

    def register_filenames(
        self, filenames: Iterable[str], token: Optional[str] = None
    ) -> str:
        """
        Register filenames behind an unguessable capability token and return
        the token; re-registering the same set returns the existing token. A
        request carrying `sw_token=<token>` may read exactly these filenames.
        Pass `token` to register an existing capability in this proxy too
        (used when one client is shared across multiple Shiny Apps in the
        process, so URLs minted for one App are accepted by another's proxy).
        Tokens live for the app's lifetime (the proxy mount is app-wide, so
        there is no per-session revocation), and only the app side can mint
        them: the proxied guard and the widget hooks never register values
        observed in requests or widget traits, which a browser controls.
        """
        key = frozenset(str(f) for f in filenames)
        if token is not None:
            self._capabilities[token] = key
            return token
        for existing_token, existing in self._capabilities.items():
            if existing == key:
                return existing_token
        token = secrets.token_urlsafe(16)
        self._capabilities[token] = key
        return token

    def authorized_filenames(self, token: Optional[str]) -> FrozenSet[str]:
        """Filenames already registered behind `token` (empty if unknown)."""
        if token is None:
            return frozenset()
        return self._capabilities.get(token, frozenset())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close"})
            return
        if scope["type"] != "http":
            raise RuntimeError(f"Unsupported scope type: {scope['type']}")
        if scope["method"] not in ("GET", "HEAD", "OPTIONS"):
            await self._simple_response(send, 405, b"Method Not Allowed")
            return

        # The Mount above strips the `/proxy/{port}` prefix into root_path
        # (starlette's Mount doesn't put the remainder in path_params)
        path = get_route_path(scope)
        if not path.startswith("/"):
            path = "/" + path

        if self._allowed_filenames is not None:
            if path.startswith(_LOOPBACK_PROXY_BLOCKED_PREFIX):
                await self._simple_response(
                    send, 403, b"Forbidden: route blocked on guarded proxies"
                )
                return
            params = parse_qs(scope.get("query_string", b"").decode("latin-1"))
            token_set = self._capabilities.get(
                params.get(_LOOPBACK_PROXY_TOKEN_PARAM, [""])[0], frozenset()
            )
            sources: List[str] = []
            by_param: Dict[str, List[str]] = {}
            for k, vs in params.items():
                if k == "files":  # comma-separated (localtileserver mosaics)
                    by_param[k] = [v for part in vs for v in part.split(",")]
                elif k in _LOOPBACK_PROXY_SOURCE_PARAMS:
                    by_param[k] = vs
                else:
                    continue
                sources.extend(by_param[k])
            if any(
                s not in self._allowed_filenames and s not in token_set for s in sources
            ):
                await self._simple_response(
                    send, 403, b"Forbidden: unregistered raster source"
                )
                return
            for prefix, route_params in _LOOPBACK_PROXY_ROUTE_SELECTORS:
                if path.startswith(prefix) and not any(
                    by_param.get(p) for p in route_params
                ):
                    await self._simple_response(
                        send,
                        403,
                        b"Forbidden: raster route requires a source selector",
                    )
                    return
        # Re-encode: `path` is percent-decoded, so forwarding it verbatim
        # would let an escaped `?` (%3F) smuggle a query string past the
        # guard above into the upstream URL.
        path = quote(path, safe="/")
        query = scope.get("query_string", b"")
        if query:
            path += "?" + query.decode("latin-1")
        req_headers = {
            k.decode("latin-1"): v.decode("latin-1")
            for k, v in scope["headers"]
            if k.decode("latin-1").lower() not in _LOOPBACK_PROXY_DROP_HEADERS
        }

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Tuple[str, Any]] = asyncio.Queue(maxsize=8)
        stop = threading.Event()

        def put(item: Tuple[str, Any]) -> None:
            if stop.is_set():
                return
            try:
                asyncio.run_coroutine_threadsafe(queue.put(item), loop).result(
                    timeout=30
                )
            except Exception:
                stop.set()
                raise _LoopbackProxyAborted

        def forward() -> None:
            conn = http.client.HTTPConnection("127.0.0.1", self._port, timeout=60)
            try:
                conn.request(scope["method"], path, headers=req_headers)
                resp = conn.getresponse()
                put(("start", (resp.status, resp.getheaders())))
                while not stop.is_set():
                    chunk = resp.read(self._CHUNK_SIZE)
                    if not chunk:
                        break
                    put(("body", chunk))
            except _LoopbackProxyAborted:
                pass
            except Exception as exc:
                put(("error", exc))
            finally:
                put(("end", None))
                conn.close()

        threading.Thread(target=forward, daemon=True).start()

        response_started = False
        response_finished = False
        try:
            while True:
                kind, payload = await queue.get()
                if kind == "start":
                    status, resp_headers = payload
                    await send(
                        {
                            "type": "http.response.start",
                            "status": status,
                            "headers": [
                                (k.lower().encode("latin-1"), v.encode("latin-1"))
                                for k, v in resp_headers
                                if k.lower() not in _LOOPBACK_PROXY_DROP_HEADERS
                            ],
                        }
                    )
                    response_started = True
                elif kind == "body":
                    await send(
                        {
                            "type": "http.response.body",
                            "body": payload,
                            "more_body": True,
                        }
                    )
                elif kind == "error":
                    if not response_started:
                        await self._simple_response(send, 502, b"Bad Gateway")
                        response_finished = True
                    break
                else:  # "end"
                    break
        except Exception:
            # Most likely the client disconnected mid-stream; the forwarding
            # thread is aborted via `stop` below and there's nothing more to send.
            response_finished = True
        finally:
            stop.set()
            if response_started and not response_finished:
                try:
                    await send({"type": "http.response.body", "body": b""})
                except Exception:
                    pass

    @staticmethod
    async def _simple_response(send: Send, status: int, body: bytes) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def mount_loopback_proxy(
    app: App, port: int, allowed_filenames: Optional[Iterable[str]] = None
) -> Optional[_LoopbackProxyApp]:
    """
    Mount `_LoopbackProxyApp(port)` at `/proxy/{port}/` on the Shiny app, so a
    server bound to 127.0.0.1:{port} in this process is reachable same-origin
    (required for remote browsers, i.e. any deployed app). Returns the mounted
    (or existing) proxy so callers can register capability tokens on it, or
    `None` if the `/proxy/{port}` path is owned by some other app.

    `allowed_filenames` is the app-wide plain allowlist: `None` (the default)
    mounts an *unguarded* proxy; any iterable — including an empty one —
    mounts a *guarded* one. Prefer capability tokens
    (`_LoopbackProxyApp.register_filenames`) for per-registration
    authorization; the plain list is app-wide.

    Idempotent per port, matched on the route *path* (not just the mount
    name): if a proxy is already mounted for this port — including one mounted
    by hand with the pre-feature recipe — it is kept, and `allowed_filenames`
    are unioned into its guard (an iterable also strengthens an unguarded
    mount to guarded). starlette matches the first route, so shadowing a
    hand-mounted unguarded proxy with a guarded one would silently leave the
    unguarded one in effect; augmenting in place avoids that.
    """
    handler = app._dependency_handler
    for route in handler.routes:
        if getattr(route, "path", "").rstrip("/") == f"/proxy/{port}":
            existing = getattr(route, "app", None)
            if not isinstance(existing, _LoopbackProxyApp):
                return None
            if allowed_filenames is not None:
                if existing._allowed_filenames is None:
                    existing._allowed_filenames = set()
                existing._allowed_filenames.update(allowed_filenames)
            return existing
    proxy = _LoopbackProxyApp(
        port, set(allowed_filenames) if allowed_filenames is not None else None
    )
    handler.mount(f"/proxy/{port}/", proxy, name=f"loopback-proxy-{port}")
    return proxy


def _add_proxy_token(url: str, token: Optional[str]) -> str:
    """
    Attach a proxy capability token to a (rewritten) tile URL. Idempotent: an
    existing token is replaced, not duplicated (shared layers are re-wired
    once per session, which must not grow the URL each time).
    """
    if token is None:
        return url
    base, sep, query = url.partition("?")
    parts = [
        p
        for p in query.split("&")
        if p and not p.startswith(f"{_LOOPBACK_PROXY_TOKEN_PARAM}=")
    ]
    parts.append(f"{_LOOPBACK_PROXY_TOKEN_PARAM}={token}")
    return base + sep + "&".join(parts)


def _rewrite_loopback_url(url: str, port: int) -> str:
    """
    Rewrite a tile URL onto the `/proxy/{port}/` mount as a *relative* URL.
    Relative (rather than root-relative) resolves against the page URL, so it
    also works when the app is served under a path prefix (Posit Connect,
    shinyapps.io).
    """
    for prefix in (
        f"http://127.0.0.1:{port}/",
        f"http://localhost:{port}/",
        f"http://0.0.0.0:{port}/",
        f"/proxy/{port}/",
    ):
        if url.startswith(prefix):
            return f"proxy/{port}/" + url[len(prefix) :]
    return url


def localtileserver_layer_proxy(w: Widget, session: Session) -> None:
    """
    Auto-wire localtileserver-backed ipyleaflet layers for deployed apps
    (no-op for any other widget).

    `get_leaflet_tile_layer()` layers carry their TileClient as a
    `tile_server` attribute (localtileserver >= 1.0.0 sets it unconditionally;
    earlier versions only set it when the client was created from a path, so
    those need upgrading). Their tile URLs default to
    `http://127.0.0.1:{port}`, which a remote browser can't reach, and the
    tile server's raster-source API (`filename`/`files`/`url` query params)
    is unauthenticated. For such a layer, mount the guarded loopback proxy,
    register the client's filenames behind a capability token (trusted
    app-side state — app-wide registration would let one session's users read
    another session's rasters by knowing their paths), and route tile URLs
    through it:

    * the layer's current `url` is rewritten (this runs before widget state
      is serialized, so the browser only ever sees the proxy URL);
    * the client's `get_tile_url()` is wrapped so restyle URLs
      (`client=True`, keyword or positional) come out proxy-relative in a
      single step — a traitlets observer alone would let the raw loopback
      URL sync to the browser first, since ipywidgets sends each trait
      change as it happens;
    * an observer on `url` backstops direct assignments (URLs not produced
      via `get_tile_url`). It rewrites, and re-attaches the token only when
      the URL's raster source was already registered for this client — it
      never registers new sources, since trait values can be pushed by the
      browser over the comm and registering from them would let a client
      poison its own allowlist. An unregistered source stays tokenless and
      the proxy refuses it (403), loudly, rather than leaking.

    localtileserver is never imported (duck-typed throughout). Set
    SHINYWIDGETS_LOOPBACK_PROXY_DISABLE=1 to opt out.
    """
    if os.environ.get("SHINYWIDGETS_LOOPBACK_PROXY_DISABLE", ""):
        return
    client = getattr(w, "tile_server", None)
    if client is None:
        return
    port = getattr(client, "server_port", None)
    url = getattr(w, "url", None)
    if port is None or not isinstance(url, str):
        return
    port = int(port)

    filenames = getattr(client, "filename", None)
    if isinstance(filenames, (list, tuple)):  # mosaic clients
        sources = [str(f) for f in filenames]
    elif filenames is not None:
        sources = [str(filenames)]
    else:
        # e.g. in-memory xarray sources, whose routes read from a server-side
        # registry (`key` param), not from a file selector — no token needed
        sources = []

    proxy = mount_loopback_proxy(session.app, port, allowed_filenames=())
    token: Optional[str] = None
    if proxy is not None and sources:
        # One capability per client, stable across Apps: a client (or shared
        # layer) reused in another Shiny App gets the same token registered
        # in that App's proxy, so URLs minted for one App work in the other
        token = getattr(client, "_shinywidgets_proxy_token", None)
        if token is None:
            token = proxy.register_filenames(sources)
            client._shinywidgets_proxy_token = token
        else:
            proxy.register_filenames(sources, token=token)
    authorized = frozenset(sources)

    if not getattr(client, "_shinywidgets_url_wrapped", False):
        orig_get_tile_url = client.get_tile_url
        try:
            sig = inspect.signature(orig_get_tile_url)
        except (TypeError, ValueError):  # pragma: no cover
            sig = None

        def get_tile_url(*args: Any, **kwargs: Any) -> str:
            result = orig_get_tile_url(*args, **kwargs)
            # `client` may be passed positionally; resolve it against the
            # real signature rather than only checking kwargs
            is_client = False
            if sig is not None:
                try:
                    is_client = bool(
                        sig.bind(*args, **kwargs).arguments.get("client", False)
                    )
                except TypeError:
                    is_client = bool(kwargs.get("client", False))
            rewritten = _rewrite_loopback_url(result, port)
            if is_client and rewritten != result:
                # Only token actual proxy URLs: attaching it to an unrelated
                # (external) URL would send the credential to that server
                return _add_proxy_token(rewritten, token)
            return result

        client.get_tile_url = get_tile_url
        client._shinywidgets_url_wrapped = True

    rewritten = _rewrite_loopback_url(url, port)
    new_url = _add_proxy_token(rewritten, token) if rewritten != url else rewritten
    if new_url != url:
        w.url = new_url  # type: ignore[attr-defined]

    # A process-global widget is opened once per session; attach the backstop
    # observer only once per widget.
    if getattr(w, "_shinywidgets_proxy_observed", False):
        return

    def _rewrite(change: Any) -> None:
        changed = change["new"]
        if not isinstance(changed, str):
            return
        new = _rewrite_loopback_url(changed, port)
        if new == changed:
            return
        changed_sources = _url_sources(changed)
        if changed_sources and all(s in authorized for s in changed_sources):
            new = _add_proxy_token(new, token)
        # Reentrant (setting a trait fires observers), but the second pass
        # sees an already-relative URL and stops.
        w.url = new  # type: ignore[attr-defined]

    w.observe(_rewrite, "url")
    w._shinywidgets_proxy_observed = True  # type: ignore[attr-defined]


def _url_sources(url: str) -> List[str]:
    """The raster sources (`filename`/`files`/`url`) a localtileserver URL reads."""
    from urllib.parse import urlparse

    params = parse_qs(urlparse(url).query)
    sources = params.get("filename", []) + params.get("url", [])
    for part in params.get("files", []):
        sources.extend(part.split(","))
    return sources


# anywidget's front-end rejects a model's `ready` promise if initialization
# (i.e., loading the widget's `_esm`) takes longer than a hard-coded 2s
# (`AbortSignal.timeout(2e3)` -> "[anywidget] Failed to initialize model.").
# `_handle_comm_msg` awaits that promise, so once it rejects, every subsequent
# Python -> browser state update is dropped (and surfaces as a console error).
# That's unsuitable outside Jupyter for widgets with multi-MB inline ESM
# bundles (keplergl's `_esm` is ~13MB), which can't compile within 2s on
# slower hardware. Serve a patched copy with a more generous budget instead.
# Interim workaround for https://github.com/manzt/anywidget/issues/1030 --
# remove this (and serve anywidget's files unmodified) once upstream makes
# the init budget configurable or stops gating comm messages on it.
ANYWIDGET_INIT_TIMEOUT_MS = 60000


def relax_anywidget_init_timeout(module_dir: str) -> str:
    """
    Return a directory holding a copy of anywidget's front-end (nbextension)
    with the hard-coded 2s model-initialization budget raised. Falls back to
    `module_dir` itself if the timeout can't be located (e.g., a future
    anywidget release restructures this code).
    """
    index = os.path.join(module_dir, "index.js")
    try:
        mtime = os.path.getmtime(index)
    except OSError:
        return module_dir

    key = (module_dir, mtime)
    if key in _anywidget_patched_dirs:
        return _anywidget_patched_dirs[key]

    patched_dir = module_dir
    with open(index, encoding="utf-8") as f:
        js = f.read()

    i = js.find("Failed to initialize model")
    if i >= 0:
        # The timeout that guards model initialization sits just before the
        # rejection; match its numeric argument (2e3 or 2000)
        m = re.search(
            r"AbortSignal\.timeout\(\s*(?:2e3|2000)\s*\)", js[max(0, i - 500) : i]
        )
        if m is not None:
            patched_dir = tempfile.mkdtemp(prefix="shinywidgets-anywidget-")
            for f_ in os.listdir(module_dir):
                src = os.path.join(module_dir, f_)
                if not os.path.isfile(src):
                    continue
                with open(src, "rb") as fin:
                    contents = fin.read()
                if f_ == "index.js":
                    contents = (
                        js[: max(0, i - 500) + m.start()]
                        + f"AbortSignal.timeout({ANYWIDGET_INIT_TIMEOUT_MS})"
                        + js[max(0, i - 500) + m.end() :]
                    ).encode("utf-8")
                with open(os.path.join(patched_dir, f_), "wb") as fout:
                    fout.write(contents)

    _anywidget_patched_dirs[key] = patched_dir
    return patched_dir


_anywidget_patched_dirs: dict[tuple[str, float], str] = {}


def jupyter_extension_path(module_name: str) -> Optional[str]:
    paths: List[str] = jupyter_path()
    for x in paths:
        dir = os.path.join(x, "nbextensions", module_name)
        if not os.path.exists(dir):
            continue
        for f in os.listdir(dir):
            if f.startswith("index") and f.endswith(".js"):
                return dir

    return None


# Approximates what `jupyter nbextension install` does to discover and copy source files
# for the extension.
# https://github.com/jupyter-server/jupyter_server/blob/e70e7be/notebook/nbextensions.py#L211-L212
# https://github.com/jupyter-widgets/widget-cookiecutter/blob/master/%7B%7Bcookiecutter.github_project_name%7D%7D/%7B%7Bcookiecutter.python_package_name%7D%7D/__init__.py
#
# N.B. for now, we're only supporting the notebook extension (not the lab extension)
# model since it's simpler to understand and maps onto the HTMLDependency() model a bit
# better (i.e., it doesn't require node and/or widget registry implementation details).
# Also, this method isn't foolproof in the sense that it's possible for the widget
# instance's __module__ to not point to the right package. An example is
# plotly's FigureWidget() pointing to the plotly package, but the actual
# dependencies actually live in a separate jupyterlab_plotly package.
def jupyter_extension_destination(w: Widget) -> str:
    with tempfile.TemporaryDirectory():
        mod: ModuleType = importlib.import_module(".", package=widget_pkg(w))

    if mod.__file__ is None:
        raise RuntimeError(f"Module {mod.__name__} has no __file__ attribute")

    if hasattr(mod, "_jupyter_nbextension_paths"):
        return mod._jupyter_nbextension_paths()[0]["dest"]
    else:
        return widget_pkg(w)


def widget_pkg(w: object) -> str:
    # Instances of builtins (e.g., "x", {}) have no __module__ attribute
    module: str = getattr(w, "__module__", None) or type(w).__module__
    return module.split(".")[0]


def parse_version(v: str) -> str:
    # version could be in node-semver format
    # which is not compatible with packaging.version.parse
    # so we strip out the leading non-numeric characters
    # e.g., ^1.2.3 -> 1.2.3
    ver = re.sub("^\\D+", "", v)
    return str(packaging.version.parse(ver))


# parsing can fail if the version is something like "*",
# but it doesn't seem vital that we obtain the _actual_ version
# since this only gets the version of the HTMLManager and module
# dependencies, which should be unique within a given session
def parse_version_safely(v: str) -> str:
    try:
        return parse_version(v)
    except Exception:
        return "0.0"
