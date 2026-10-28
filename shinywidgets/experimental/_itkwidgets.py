"""
EXPERIMENTAL: itkwidgets 1.0a support via imjoy-rpc over Shiny messages.

itkwidgets 1.0a is not an ipywidgets package -- its ``Viewer`` is an ImJoy
plugin that talks to a browser-side ImJoy core over RPC (in Jupyter, over a
kernel comm with target name ``imjoy_rpc``). This module re-implements that
transport with Shiny custom messages / inputs instead of a Jupyter comm, so
``itkwidgets.viewer.Viewer`` works inside a Shiny app.

Usage:

.. code-block:: python

    import numpy as np
    from itkwidgets import Viewer
    from shiny import App, render, ui
    from shinywidgets.experimental import itkwidgets as sw_itk

    app_ui = ui.page_fillable(
        sw_itk.imjoy_head(),
        ui.card(ui.output_ui("viewer")),
    )


    def server(input, output, session):
        sw_itk.register_imjoy_session(session, input)

        @render.ui
        def viewer():
            vol = np.random.rand(64, 64, 64).astype(np.float32)
            return sw_itk.render_viewer(session, Viewer(image=vol))


    app = App(app_ui, server)

Notes / requirements:

* ``itkwidgets>=1.0a55`` has dependency rot: it needs ``zarr<3`` (which needs
  ``numcodecs<0.13`` on current Python), ``ngff-zarr<0.15``, and an
  undeclared ``urllib3`` dependency. See docs/widget-reports/itkwidgets.
* The viewer frontend (itk-vtk-viewer) is loaded from
  ``itkwidgets.viewer_config.ITK_VIEWER_SRC`` -- an IPFS public-gateway URL
  that is currently unreliable (the gateway is being sunset). Set the
  ``ITK_VIEWER_SRC`` environment variable to a self-hosted itk-vtk-viewer
  ``index.html`` (e.g. the npm package ``itk-vtk-viewer@14.51.0`` ``dist/``
  directory served as static assets) for reliable rendering.
* Viewer getters (``await viewer.get_image_color_map()`` etc.) must not be
  awaited inside a reactive effect: while an async effect is awaiting, Shiny
  does not dispatch the input effect that delivers the RPC response, so the
  call deadlocks. Run them in a background task (``asyncio.ensure_future`` /
  ``reactive.ExtendedTask``) and set results from a done callback.
* Event listeners registered over RPC
  (``viewer.viewer_rpc.itk_viewer.registerEventListener``) are single-use:
  the callback is consumed by the first event. Re-register inside the
  callback to keep receiving events.

This module is experimental and may change or be removed in any release.
"""

# imjoy_rpc/itkwidgets are optional dependencies of this experimental module
# and are intentionally not installed in the dev environment.
# pyright: reportMissingImports=false

from __future__ import annotations

import asyncio
import base64
import json
import os
import queue as _queue
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from htmltools import HTMLDependency

__all__ = [
    "imjoy_head",
    "register_imjoy_session",
    "render_viewer",
    "ITK_VIEWER_SRC_ENV",
]

ITK_VIEWER_SRC_ENV = "ITK_VIEWER_SRC"
_DEBUG = os.environ.get("SHINYWIDGETS_IMJOY_DEBUG", "") != ""


def _log(msg: str) -> None:
    if _DEBUG:
        print(f"[shinywidgets.imjoy {time.time():.2f}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# itkwidgets / imjoy_rpc patching (must happen before the first Viewer)
# ---------------------------------------------------------------------------


def _patch_itkwidgets() -> Any:
    try:
        import itkwidgets.viewer as itv
    except ImportError as e:
        raise ImportError(
            "The experimental itkwidgets integration requires "
            "`pip install 'itkwidgets>=1.0a55'` (plus `numcodecs<0.13`, "
            "`ngff-zarr<0.15`, and `urllib3`; see "
            "docs/widget-reports/itkwidgets/report.md)."
        ) from e

    from itkwidgets.integrations.environment import Env

    if getattr(itv, "_shinywidgets_patched", False):
        return itv

    class _CellWatcherStub:
        """Stand-in for itkwidgets.cell_watcher.CellWatcher (which needs
        pyzmq + an IPython kernel). Viewer code calls these methods on it."""

        def __init__(self) -> None:
            self.results: Dict[str, Any] = {}
            self._ready: Dict[str, bool] = {}

        def add_viewer(self, parent: str) -> None:
            self._ready[parent] = False

        def update_viewer_status(self, parent: str, status: bool) -> None:
            self._ready[parent] = status

        def viewer_ready(self, parent: str) -> bool:
            return self._ready.get(parent, False)

        def _callback(self, name: str, future: Any) -> None:
            pass

    class _DisplayStub:
        """Stand-in for the object IPython's display(..., display_id=...)
        returns; ViewerRPC uses it to embed static screenshots in notebook
        cells, which is a no-op under Shiny."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def display(self, *args: Any, **kwargs: Any) -> None:
            pass

        def update(self, *args: Any, **kwargs: Any) -> None:
            pass

    def _setup_queueing_threadsafe(self: Any) -> None:
        """Replacement for Viewer._setup_queueing: IPython's
        BackgroundJobManager requires a live IPython shell; a plain thread
        running the same queue worker is equivalent."""
        self.queue = _queue.Queue()
        self.deferred_queue = _queue.Queue()
        self.bg_thread = threading.Thread(target=self.queue_worker, daemon=True)
        self.bg_thread.start()

    async def _run_shiny(self: Any, ctx: dict) -> None:
        """Replacement for ViewerRPC.run without the notebook-only pieces:
        the static screenshot embedding (IPython display) and its
        'screenshotTaken' listener, plus the 10 s settle wait between them.

        The 'renderedImageAssigned' listener is re-armed after each firing
        because imjoy-rpc encodes function arguments as single-use callbacks.
        """
        from itkwidgets._initialization_params import (
            build_config,
            defer_for_data_render,
        )

        ui = self._init_viewer_kwargs.get("ui", None)
        config = build_config(ui)
        itk_viewer = await itv.api.createWindow(
            name=f"itkwidgets viewer {itv._viewer_count}",
            type="itk-vtk-viewer",
            src=itv.ITK_VIEWER_SRC,
            fullscreen=True,
            data=self.init_data,
            config=config,
        )
        itv._viewer_count += 1

        self.set_default_ui_values(itk_viewer)
        self.itk_viewer = itk_viewer
        self.wid = itk_viewer.config.window_id

        def on_rendered(data: Any) -> None:
            self.set_event(data)
            itk_viewer.registerEventListener("renderedImageAssigned", on_rendered)

        itk_viewer.registerEventListener("renderedImageAssigned", on_rendered)
        if not defer_for_data_render(self.init_data):
            itv._cell_watcher.update_viewer_status(self.parent, True)
        asyncio.get_running_loop().call_soon_threadsafe(self.viewer_event.set)

    itv.ENVIRONMENT = Env.JUPYTER  # take the ViewerRPC path (not HYPHA)
    itv._cell_watcher = _CellWatcherStub()
    itv.display = lambda *args, **kwargs: _DisplayStub()
    itv.Viewer._setup_queueing = _setup_queueing_threadsafe
    itv.ViewerRPC.run = _run_shiny

    if os.environ.get(ITK_VIEWER_SRC_ENV):
        itv.ITK_VIEWER_SRC = os.environ[ITK_VIEWER_SRC_ENV]

    itv._shinywidgets_patched = True
    return itv


# ---------------------------------------------------------------------------
# Buffer helpers, copied from imjoy_rpc.connection.jupyter_connection
# (importing that module would require ipykernel, which we deliberately avoid)
# ---------------------------------------------------------------------------

_binary_types = (memoryview, bytearray, bytes)


def _put_buffers(state: Any, buffer_paths: List[Any], buffers: List[bytes]) -> None:
    for buffer_path, buffer in zip(buffer_paths, buffers):
        obj = state
        for key in buffer_path[:-1]:
            obj = obj[key]
        obj[buffer_path[-1]] = buffer if isinstance(buffer, bytes) else buffer.tobytes()


def _separate_buffers(
    substate: Any, path: List[Any], buffer_paths: List[Any], buffers: List[Any]
) -> Any:
    if isinstance(substate, (list, tuple)):
        items: List[Any] = list(substate)
        is_cloned = False
        for i, v in enumerate(items):
            if isinstance(v, _binary_types):
                is_cloned = True
                items[i] = None
                buffers.append(v)
                buffer_paths.append(path + [i])
            elif isinstance(v, (dict, list, tuple)):
                v_new = _separate_buffers(v, path + [i], buffer_paths, buffers)
                if v is not v_new:
                    is_cloned = True
                    items[i] = v_new
        if is_cloned:
            substate = items
    elif isinstance(substate, dict):
        is_cloned = False
        for k, v in substate.items():
            if isinstance(v, _binary_types):
                if not is_cloned:
                    substate = dict(substate)
                    is_cloned = True
                del substate[k]
                buffers.append(v)
                buffer_paths.append(path + [k])
            elif isinstance(v, (dict, list, tuple)):
                v_new = _separate_buffers(v, path + [k], buffer_paths, buffers)
                if v is not v_new:
                    if not is_cloned:
                        substate = dict(substate)
                        is_cloned = True
                    substate[k] = v_new
    else:
        raise ValueError("expected state to be a list or dict, not %r" % substate)
    return substate


def _remove_buffers(state: Any) -> Any:
    buffer_paths: List[Any] = []
    buffers: List[Any] = []
    state = _separate_buffers(state, [], buffer_paths, buffers)
    return state, buffer_paths, buffers


# ---------------------------------------------------------------------------
# Python side of the imjoy-rpc protocol over Shiny messages
# ---------------------------------------------------------------------------


class _ShinyImjoyConnection:
    """Mirror of imjoy_rpc's JupyterCommConnection, over Shiny messages."""

    def __init__(self, session: Any, connection_id: str, container_id: str):
        from imjoy_rpc.utils import MessageEmitter

        # MessageEmitter is not easily subclassable w/o its logger plumbing;
        # compose instead.
        self._emitter = MessageEmitter(None)
        self.session = session
        self.connection_id = connection_id
        self.container_id = container_id
        self.peer_id = str(uuid.uuid4())
        self._loop = asyncio.get_running_loop()

    # MessageEmitter interface used by imjoy_rpc.RPC
    def on(self, event: str, handler: Callable) -> None:
        self._emitter.on(event, handler)

    def once(self, event: str, handler: Callable) -> None:
        self._emitter.once(event, handler)

    def off(
        self, event: Optional[str] = None, handler: Optional[Callable] = None
    ) -> None:
        self._emitter.off(event, handler)

    def _fire(self, event: str, data: Any) -> None:
        self._emitter._fire(event, data)

    # -- outgoing (Python -> browser) ------------------------------------
    def emit(self, msg: Dict[str, Any]) -> None:
        if msg["type"] == "method" and msg.get("name") == "createWindow":
            window_id = "imjoy_window_" + str(uuid.uuid4())
            msg["args"][0]["window_id"] = window_id
            msg["args"][0]["_container_id"] = self.container_id
        msg, buffer_paths, buffers = _remove_buffers(msg)
        if len(buffers) > 0:
            msg["__buffer_paths__"] = buffer_paths
        payload = json.dumps(
            {
                "connection_id": self.connection_id,
                "data": msg,
                "buffers": [
                    base64.b64encode(bytes(b)).decode("ascii") for b in buffers
                ],
            }
        )
        _log(
            f"emit type={msg['type']} name={msg.get('name')} bufs={sum(len(b) for b in buffers)}"
        )

        async def _send() -> None:
            await self.session.send_custom_message("imjoy_rpc_msg", payload)

        # send_custom_message writes directly to the websocket, so send right
        # away. Do NOT route through session.on_flush: if the current effect
        # is awaiting this call's response (e.g. viewer getters), the flush
        # would wait for the effect to finish and deadlock the RPC.
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is not None and running is self._loop:
            running.create_task(_send())
        else:
            asyncio.run_coroutine_threadsafe(_send(), self._loop)

    # -- incoming (browser -> Python) --------------------------------------
    def handle_message(self, data: Dict[str, Any], buffers: List[bytes]) -> None:
        if "__buffer_paths__" in data:
            buffer_paths = data.pop("__buffer_paths__")
            _put_buffers(data, buffer_paths, buffers)
        # Connections are dedicated (one per viewer), and the imjoy core
        # stamps some routed messages (e.g. callbacks from the viewer window)
        # with its own peer id rather than echoing ours, so accept everything
        # addressed to this connection.
        if "type" in data:
            self._fire(data["type"], data)

    # RPC lifecycle no-ops (the Shiny websocket is always "connected")
    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass


class _ImjoyShinyManager:
    """Mirror of imjoy_rpc's JupyterCommManager: holds exported interfaces
    and codecs, and creates one RPC per browser connection."""

    def __init__(self, rpc_context: Any):
        self.rpc_context = rpc_context
        self.default_config: Dict[str, Any] = {}
        self.interface: Optional[Dict[str, Any]] = None
        self._codecs: Dict[str, Any] = {}
        self.clients: Dict[str, Any] = {}
        self.exports: Dict[str, Dict[str, Any]] = {}
        self.latest_export_id: Optional[str] = None

    # called via patched api.registerCodec
    def register_codec(self, config: Dict[str, Any]) -> None:
        from imjoy_rpc.utils import dotdict

        assert "name" in config
        assert "encoder" in config or "decoder" in config
        if "type" in config:
            for tp in list(self._codecs.keys()):
                codec = self._codecs[tp]
                if codec.type == config["type"] or tp == config["name"]:
                    del self._codecs[tp]
        self._codecs[config["name"]] = dotdict(config)

    # called via patched api.export (e.g. when a Viewer is constructed)
    def set_interface(
        self, interface: Any, config: Optional[Dict[str, Any]] = None
    ) -> Any:
        from imjoy_rpc.utils import dotdict

        cfg = dotdict(config or self.default_config)
        cfg.id = str(uuid.uuid4())
        cfg.name = cfg.name or cfg.id
        cfg.allow_execution = cfg.allow_execution or False
        cfg.version = cfg.version or "0.1.0"
        cfg.api_version = cfg.api_version or "0.2.3"
        cfg.description = cfg.description or "[TODO: add description]"
        self.default_config = cfg
        self.interface = interface
        self.exports[cfg.id] = {"interface": interface, "config": cfg}
        self.latest_export_id = cfg.id
        _log(f"export registered: {cfg.name} ({cfg.id})")
        return asyncio.gather()

    def init(self, config: Optional[Dict[str, Any]] = None) -> None:
        def setup() -> None:
            pass

        self.set_interface({"setup": setup}, config)

    # -- connection lifecycle ----------------------------------------------
    def browser_ready(
        self,
        session: Any,
        connection_id: str,
        container_id: str,
        export_id: Optional[str] = None,
    ) -> _ShinyImjoyConnection:
        """Browser glue is listening; start the handshake by sending
        imjoyRPCReady (mirror of JupyterCommManager._create_new_connection)."""
        from imjoy_rpc.rpc import RPC
        from imjoy_rpc.utils import dotdict

        connection = _ShinyImjoyConnection(session, connection_id, container_id)
        export = self.exports.get(export_id) if export_id else None
        if export is None:
            if export_id:
                _log(f"WARNING: unknown export {export_id}, using latest")
            export = self.exports.get(self.latest_export_id or "", None)
        if export is None:
            raise RuntimeError("imjoy: browser connected but no interface was exported")
        interface = export["interface"]
        export_config = export["config"]

        def initialize(data: Dict[str, Any]) -> None:
            cfg = data["config"]
            cfg["id"] = export_config.get("id", connection_id)
            rpc = RPC(connection, self.rpc_context, config=cfg, codecs=self._codecs)
            rpc.set_interface(interface)
            rpc.init()

            def patch_api(_: Any) -> None:
                api = rpc.get_remote() or dotdict()
                api.init = self.init
                api.export = self.set_interface
                api.dispose = rpc.disconnect
                api.registerCodec = self.register_codec
                api.disposeObject = rpc.dispose_object
                api.register_codec = self.register_codec
                api.dispose_object = rpc.dispose_object
                api._rpc = rpc

            rpc.on("remoteReady", patch_api)
            rpc.on("error", lambda e: _log(f"RPC error: {e}"))
            self.clients[connection_id] = rpc

        connection.once("initialize", initialize)
        connection.emit(
            {
                "type": "imjoyRPCReady",
                "config": dict(export_config),
                "peer_id": connection.peer_id,
            }
        )
        return connection


_manager: Optional[_ImjoyShinyManager] = None
_CONNECTIONS: Dict[str, _ShinyImjoyConnection] = {}


def _get_manager() -> _ImjoyShinyManager:
    global _manager
    if _manager is not None:
        return _manager

    _patch_itkwidgets()
    import imjoy_rpc

    _manager = _ImjoyShinyManager(imjoy_rpc._rpc_context)
    # Route imjoy_rpc's module-level api (api.export etc.) to our manager
    # instead of letting it auto-detect a (nonexistent) Jupyter kernel.
    wrapper = imjoy_rpc._rpc_context.api
    wrapper._ApiWrapper__initialized = True  # pyright: ignore[reportAttributeAccessIssue]
    wrapper["init"] = _manager.init
    wrapper["export"] = _manager.set_interface
    wrapper["registerCodec"] = _manager.register_codec
    wrapper["register_codec"] = _manager.register_codec
    return _manager


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def imjoy_head() -> List[Any]:
    """Dependencies to include in the app UI (e.g. via ``ui.head_content``)."""
    return [
        HTMLDependency(
            name="imjoy-core",
            version="0.14.5",
            source={"href": "https://cdn.jsdelivr.net/npm/imjoy-core@0.14.5/dist"},
            script=[{"src": "imjoy-loader.js"}],
        ),
        HTMLDependency(
            name="shinywidgets-imjoy",
            version="1",
            source={"package": "shinywidgets", "subdir": "static"},
            script=[{"src": "imjoy-bridge.js"}],
        ),
    ]


def register_imjoy_session(session: Any, input: Any) -> None:
    """Wire a Shiny session to the imjoy bridge (call once per session)."""
    from shiny import reactive

    _get_manager()

    @reactive.effect
    @reactive.event(input.imjoy_rpc_send)
    def _on_imjoy_msg() -> None:
        payload = json.loads(input.imjoy_rpc_send())
        cid = payload["connection_id"]
        data = payload["data"]
        buffers = [base64.b64decode(b) for b in payload.get("buffers", [])]
        if data.get("type") == "browserReady":
            _log(f"browserReady {cid}")
            mgr = _get_manager()
            _CONNECTIONS[cid] = mgr.browser_ready(
                session,
                cid,
                payload.get("container_id", ""),
                payload.get("export_id"),
            )
        elif cid in _CONNECTIONS:
            _CONNECTIONS[cid].handle_message(data, buffers)
        else:
            _log(f"message for unknown connection {cid}: {data.get('type')}")

    def _cleanup() -> None:
        for cid in [c for c, conn in _CONNECTIONS.items() if conn.session is session]:
            del _CONNECTIONS[cid]

    session.on_ended(_cleanup)


def render_viewer(
    session: Any,
    viewer: Any,
    *,
    width: str = "100%",
    height: str = "100%",
) -> Any:
    """Connect a freshly-constructed ``itkwidgets.Viewer`` to the browser.

    Returns the container ``ui.div`` to return from a ``@render.ui`` output.
    The viewer mounts inline into this div once the page loads.
    """
    from shiny import ui

    mgr = _get_manager()
    connection_id = "imjoy_" + str(uuid.uuid4())
    container_id = connection_id + "_container"
    # Bind this connection to the most recent api.export() (i.e. the Viewer
    # that was just constructed in the calling render function).
    export_id = mgr.latest_export_id

    async def _send() -> None:
        await session.send_custom_message(
            "imjoy_connect",
            json.dumps(
                {
                    "connection_id": connection_id,
                    "container_id": container_id,
                    "export_id": export_id,
                }
            ),
        )

    session.on_flush(lambda: asyncio.ensure_future(_send()), once=True)
    return ui.div(
        id=container_id,
        style=f"width:{width}; height:{height}; position:relative;",
    )
