from __future__ import annotations

import json
import logging
import os
import sys
from base64 import b64decode
from contextlib import contextmanager
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Union,
    cast,
)
from uuid import uuid4
from weakref import WeakSet, ref

import ipywidgets
from packaging.version import Version

from ._render_widget import render_widget

__protocol_version__ = ipywidgets._version.__protocol_version__
DOMWidget = ipywidgets.widgets.DOMWidget
Layout = ipywidgets.widgets.Layout
Widget = ipywidgets.widgets.Widget
_remove_buffers = ipywidgets.widgets.widget._remove_buffers
from htmltools import HTMLDependency, TagList
from shiny import Session, reactive
from shiny.http_staticfiles import StaticFiles
from shiny.reactive._core import (
    get_current_context,  # pyright: ignore[reportPrivateImportUsage]
)
from shiny.session import get_current_session, require_active_session, session_context

from ._as_widget import as_widget, pydeck_has_widget
from ._bokeh import _bokeh_dependency, bokeh_extension_assets, guard_widget_close
from ._cdn import SHINYWIDGETS_CDN_ONLY, SHINYWIDGETS_EXTENSION_WARNING
from ._comm import BufferType, OrphanedShinyComm, ShinyComm, ShinyCommManager
from ._dependencies import custom_elements_dependency, require_dependencies, widget_pkg
from ._render_widget_base import WidgetRenderContext, is_closed_widget
from ._utils import package_dir
from ._widget_registry import WIDGET_INSTANCE_MAP

logger = logging.getLogger("shinywidgets")

__all__ = (
    "register_widget",
    "reactive_read",
    "session_lifetime",
)


# --------------------------------------------------------------------------------------------
# When a widget is initialized, also initialize a communication channel (via the Shiny
# session). Note that when the comm is initialized, it also sends the initial state of
# the widget.
# --------------------------------------------------------------------------------------------
def init_shiny_widget(w: Widget):
    if is_unused_pydeck_widget(w):
        retire_unused_widget(w)
        return
    plotly_version = unsupported_plotly_version(w)
    if plotly_version is not None:
        raise RuntimeError(PLOTLY_VERSION_MESSAGE.format(version=plotly_version))
    session = get_current_session()
    if session is None:
        if importing_lonboard() or importing_ipycanvas():
            return
        raise RuntimeError(
            "shinywidgets requires that all ipywidgets be constructed within an active Shiny session"
        )
    # Wait until we're in a "real" session before doing anything
    # (i.e., on the 1st run of an Express app, it's too early to do anything)
    if session.is_stub_session():
        return
    # Break out of any module-specific session. Otherwise, input.shinywidgets_comm_send
    # will be some module-specific copy.
    session = session.root_scope()

    # If this is the first time we've seen this session, initialize some things
    if session not in SESSIONS:
        SESSIONS.add(session)
        COMM_MANAGERS[session.id] = ShinyCommManager()

        # Somewhere inside ipywidgets, it makes requests for static files
        # under the publicPath set by the webpack.config.js file.
        session.app._dependency_handler.mount(
            "/dist/",
            StaticFiles(directory=os.path.join(package_dir("shinywidgets"), "static")),
            name="shinywidgets-static-resources",
        )

        # Handle messages from the client. Note that widgets like qgrid send client->server messages
        # to figure out things like what filter to be shown in the table.
        @reactive.effect
        @reactive.event(session.input.shinywidgets_comm_send)
        def _():
            handle_client_comm_msg(
                session, json.loads(session.input.shinywidgets_comm_send())
            )

        def _cleanup_session_state():
            SESSIONS.remove(session)
            COMM_MANAGERS.pop(session.id).active = False
            # Cleanup any widgets that were created in this session. Use the same
            # close_widget() helper as render cleanup (not a plain widget.close())
            # so these widgets also keep a working model_id afterwards -- other
            # live widgets (e.g. a sibling session's container that still lists
            # this widget as a child) may still read it.
            for id in SESSION_WIDGET_ID_MAP[session.id]:
                widget = WIDGET_INSTANCE_MAP.get(id)
                if widget:
                    close_widget(widget)
            del SESSION_WIDGET_ID_MAP[session.id]
            KEPT_WIDGETS.pop(session.id, None)

        session.on_ended(_cleanup_session_state)

    if isinstance(w.comm, ShinyComm):
        # The browser opened this comm (see open_client_comm()) and already has
        # the model, so there's nothing to send; just own it for session cleanup.
        SESSION_WIDGET_ID_MAP.setdefault(session.id, []).append(w.comm.comm_id)
        return

    # Make sure window.require() calls made by 3rd party widgets
    # (via handle_comm_open() -> new_model() -> loadClass() -> requireLoader())
    # actually point to directories served locally by shiny
    if SHINYWIDGETS_CDN_ONLY:
        widget_deps: List[HTMLDependency] = []
    else:
        widget_deps = require_dependencies(w, session, SHINYWIDGETS_EXTENSION_WARNING)

    # By the time we get here, the user has already had an opportunity to specify a model_id,
    # so it isn't yet populated, generate a random one so we can assign the same id to the comm
    if getattr(w, "_model_id", None) is None:
        w._model_id = uuid4().hex

    id = cast(str, w._model_id)

    if any(widget_pkg(cls) == "perspective" for cls in type(w).__mro__):
        widget_deps.append(custom_elements_dependency())
    open_keys: Dict[str, object] = {}
    if getattr(w, "_model_module", None) == "@bokeh/jupyter_bokeh":
        widget_deps.append(_bokeh_dependency())
        ext = bokeh_extension_assets(w, session)
        widget_deps.extend(ext.deps)
        if ext.module_urls or ext.module_exports:
            # ES modules load via dynamic import() client-side (default
            # exports get assigned to globals); they can't ride the
            # dependency channel since import() must be awaited.
            open_keys["modules"] = {
                "urls": ext.module_urls,
                "exports": ext.module_exports,
            }
        # BokehModel.close() is not idempotent; guard against double close.
        guard_widget_close(w)
    elif any(widget_pkg(cls) == "k3d" for cls in type(w).__mro__):
        close_comm_on_close(w)

    if any(widget_pkg(cls) == "itables" for cls in type(w).__mro__):
        # itables' bundle replaces the global `$` when its module is evaluated (see
        # protectPageJQuery() in js/src/utils.ts), which happens after this open
        open_keys["protect_jquery"] = True

    # Since the actual ShinyComm() is initialized _after_ the Widget is initialized,
    # and Widget.__init__() includes a call to Widget.open() which opens an unnecessary
    # comm, we just set the comm to a dummy comm for now (to avoid unnecessary work)
    w.comm = OrphanedShinyComm(id)

    # Capture the render (if any) now, so the deferred open below can re-enter it:
    # widgets created lazily while serializing (e.g. default Layout/Style models)
    # then get the same cleanup as this widget instead of living until session end.
    render_ctx = (
        WidgetRenderContext.get_render_context()
        if WidgetRenderContext.is_rendering_widget()
        else None
    )

    # Shiny keeps every Effect (destroyed or not) registered with session.on_ended
    # until the session ends, so the effect below must not hold the widget strongly:
    # that would keep every re-rendered widget alive for the rest of the session.
    w_ref = ref(w)

    # Schedule the opening of the comm to happen sometime after this init function.
    # This is important for widgets like plotly that do additional initialization that
    # is required to get a valid widget state.
    @reactive.effect(priority=99999)
    def _open_shiny_comm():

        _open_shiny_comm.destroy()

        w = w_ref()
        # Closed before it was opened (explicitly, or because its render was
        # invalidated): leave it closed rather than reopening it.
        if w is None or WIDGET_INSTANCE_MAP.get(id) is not w:
            return

        with WidgetRenderContext.resumed(render_ctx):
            # Plotly's display hook snapshots the data and layout for get_state().
            # https://github.com/plotly/plotly.py/blob/0089f32/packages/python/plotly/plotly/basewidget.py#L734-L738
            # ipympl's sets _data_url, the image the frontend first paints
            # (as_widget() already drew it, unless the Canvas was never coerced).
            # Other display hooks can create preview widgets, causing an infinite
            # widget-creation loop (e.g. pythreejs, #244).
            pkgs = {widget_pkg(cls) for cls in type(w).__mro__}
            if "plotly" in pkgs or (
                "ipympl" in pkgs and not getattr(w, "_data_url", "")
            ):
                w._repr_mimebundle_()
            if any(widget_pkg(cls) == "lonboard" for cls in type(w).__mro__):
                own_lonboard_controls(w)

            # Now, get the state
            state, buffer_paths, buffers = _remove_buffers(w.get_state())

        # Initialize the comm -- this sends widget state to the frontend
        w.comm = ShinyComm(
            comm_id=id,
            comm_manager=COMM_MANAGERS[session.id],
            session=session,
            target_name="jupyter.widget",
            data={"state": state, "buffer_paths": buffer_paths},
            buffers=cast(BufferType, buffers),
            # TODO: should this be hard-coded?
            metadata={"version": __protocol_version__},
            html_deps=session._process_ui(TagList(*widget_deps))["deps"],
            **open_keys,
        )

        flush_ipycanvas_manager(w)

    # If the widget initialized in a reactive _output_ context, then cleanup the widget
    # when the context gets invalidated. Use the render output's Context (captured by
    # WidgetRenderContext) rather than the current Context, because the widget may be
    # constructed inside a reactive.isolate() block whose temporary Context gets
    # invalidated prematurely (e.g., when upstream reactive sources change).
    if render_ctx is not None:
        owned = RENDER_OWNED_WIDGETS.get(render_ctx.id)
        if owned is not None:
            owned.append(w)
        else:
            # The widget must already be in the list before registering the
            # on_invalidate callback below: Context.on_invalidate() runs its
            # callback immediately if the context is already invalidated (e.g. a
            # render that invalidates itself), and that callback pops this exact
            # list to close it. Registering first would pop an empty list and
            # leave `w` appended to an orphaned one afterwards, never closed.
            RENDER_OWNED_WIDGETS[render_ctx.id] = [w]
            ctx = render_ctx

            def on_close():
                with session_context(session):
                    close_render_widgets(session, RENDER_OWNED_WIDGETS.pop(ctx.id, []))

            ctx.on_invalidate(on_close)

    # Keep track of what session this widget belongs to (so we can close it when the
    # session ends)
    SESSION_WIDGET_ID_MAP.setdefault(session.id, []).append(id)

    # ipycanvas canvases route their draw commands through a module-level
    # manager widget (shared by every canvas in the process), so swap in a
    # per-canvas one before anything walks or serializes the widget tree. This
    # must happen after _open_shiny_comm was registered above: the manager's
    # own comm then opens after this widget's (effects flush FIFO within a
    # priority), so the manager's initial commands can safely reference this
    # widget's model.
    if any(widget_pkg(cls) == "ipycanvas" for cls in type(w).__mro__):
        own_ipycanvas_manager(w)

    # Some widget's JS make external requests for static files (e.g.,
    # ipyleaflet markers) under this resource path. Note that this assumes that
    # we're setting the data-base-url attribute on the <body> (which we should
    # be doing on load in js/src/output.ts)
    # https://github.com/jupyter-widgets/widget-cookiecutter/blob/9694718/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js#L8
    for widget_dep in widget_deps:
        if not widget_dep.source:
            continue
        src_dir = widget_dep.source.get("subdir", "")
        if src_dir:
            session.app._dependency_handler.mount(
                f"/nbextensions/{widget_dep.name}",
                StaticFiles(directory=src_dir),
                name=f"{widget_dep.name}-nbextension-static-resources",
            )


# TODO: can we restore the widget constructor in a sensible way?
Widget.on_widget_constructed(init_shiny_widget)  # type: ignore


def handle_client_comm_msg(session: Session, msg: Dict[str, Any]) -> None:
    """Route a message the browser sent on the `shinywidgets_comm_send` input."""
    msg = _decode_comm_buffers(msg)
    header = msg.get("header")
    msg_type = header.get("msg_type") if isinstance(header, dict) else None
    if msg_type == "comm_open":
        open_client_comm(session, msg)
    elif msg_type == "comm_close":
        close_client_comm(session, msg)
    else:
        comm = COMM_MANAGERS[session.id].comms.get(msg["content"]["comm_id"])
        if comm is not None:
            comm.handle_msg(msg)


def open_client_comm(session: Session, msg: Dict[str, Any]) -> None:
    """
    Construct the Python counterpart of a model the browser created (e.g.
    bqplot's toolbar PanZoom), the way a kernel's `jupyter.widget` comm target
    does. Without it, the browser's `IPY_MODEL_<id>` references to the model
    can't resolve on the Python side.
    """
    content = msg["content"]
    comm_id = content["comm_id"]
    target = content.get("target_name")
    if target != "jupyter.widget":
        logger.warning(
            "Ignoring a browser comm_open for comm %s: unsupported target %r",
            comm_id,
            target,
        )
        return
    manager = COMM_MANAGERS[session.id]
    # The widget registry is process-wide, so this also covers widgets of other
    # sessions and ones constructed here whose comm hasn't been opened yet.
    if comm_id in manager.comms or comm_id in WIDGET_INSTANCE_MAP:
        logger.warning(
            "Ignoring a browser comm_open for comm %s, which is already in use",
            comm_id,
        )
        return
    comm = ShinyComm.from_client(comm_id, manager, target, session)
    try:
        comm.dispatch_client_msg(msg, lambda: Widget.handle_comm_opened(comm, msg))
    except Exception:
        logger.exception(
            "Failed to construct the widget for browser-opened comm %s", comm_id
        )
        close_client_comm(session, msg)


def close_client_comm(session: Session, msg: Dict[str, Any]) -> None:
    """The browser closed a comm: close the widget without publishing a comm_close."""
    comm_id = msg["content"]["comm_id"]
    comm = COMM_MANAGERS[session.id].comms.get(comm_id)
    if comm is None:
        return
    comm.handle_close(msg)
    w = WIDGET_INSTANCE_MAP.get(comm_id)
    if w is not None and w.comm is comm:
        close_widget(w)


def importing_lonboard() -> bool:
    """
    Is lonboard's `Map` class body executing (i.e., is lonboard mid-import)?

    That class body constructs `Map`'s default controls (and their sub-widgets)
    outside any session. They're shared by every `Map`, so they can't belong to a
    session anyway: `own_lonboard_controls()` swaps them for per-session copies
    before display.
    """
    lonboard = sys.modules.get("lonboard")
    # lonboard.Map is only bound once its class body has finished executing
    return lonboard is not None and not hasattr(lonboard, "Map")


def importing_ipycanvas() -> bool:
    """
    Is ipycanvas's `canvas` module executing (i.e., is ipycanvas mid-import)?

    Importing ipycanvas constructs a module-level `_CanvasManager` widget
    (which relays every canvas's draw commands to the browser) outside any
    session. It's shared by every canvas, so it can't belong to a session
    anyway: `own_ipycanvas_manager()` swaps it for a per-canvas copy before
    display.
    """
    canvas_mod = sys.modules.get("ipycanvas.canvas")
    # _CANVAS_MANAGER is only bound once canvas.py has finished executing
    return canvas_mod is not None and not hasattr(canvas_mod, "_CANVAS_MANAGER")


def own_ipycanvas_manager(w: Widget) -> None:
    """
    Give an ipycanvas canvas its own draw-command manager.

    Every canvas's `_canvas_manager` trait defaults to a module-level
    `_CanvasManager`, constructed when ipycanvas was imported (outside any
    session, so it has no comm, and it would leak one session's draw commands
    into another's browser). Replace it with a fresh manager, constructed here
    (inside the session, so it gets a comm of its own) before the canvas's
    initial state is serialized. The manager caches commands until its comm
    opens (see flush_ipycanvas_manager()), since drawing commands sent before
    then (e.g., while the render function is still running) would otherwise
    be silently dropped.

    Note this means `ipycanvas.hold_canvas()` (which batches commands by
    toggling the shared manager) has no effect under shinywidgets: drawing
    still works, but each command is sent individually.
    """
    canvas_mod = sys.modules.get("ipycanvas.canvas")
    shared = getattr(canvas_mod, "_CANVAS_MANAGER", None) if canvas_mod else None
    if shared is None:
        return
    if getattr(w, "_canvas_manager", None) is not shared:
        return
    setattr(w, "_canvas_manager", type(shared)(caching=True))


def flush_ipycanvas_manager(w: Widget) -> None:
    """
    Flush an ipycanvas draw-command manager whose comm just opened.

    Managers made by own_ipycanvas_manager() cache their commands (so drawing
    that happens before the comm opens isn't lost); now that the browser can
    receive them, send the backlog and go back to sending each command as it
    comes.
    """
    if widget_pkg(w) != "ipycanvas":
        return
    if not getattr(w, "_caching", False):
        return
    # flush() is a no-op unless _caching is set, so flush the backlog before
    # turning caching off (the order hold_canvas() uses)
    w.flush()  # type: ignore
    setattr(w, "_caching", False)


def is_unused_pydeck_widget(w: Widget) -> bool:
    """
    Is `w` one of the `DeckGLWidget`s that pydeck >= 0.9 constructs (e.g., to probe
    for Jupyter support) but can never display?
    """
    return widget_pkg(w) == "pydeck" and not pydeck_has_widget()


PLOTLY_VERSION_MESSAGE = (
    "shinywidgets requires plotly >= 5.12, but plotly {version} is installed. "
    "Older plotly versions' FigureWidget is incompatible with the widget "
    "manager shinywidgets uses (it renders as a blank output with no error; "
    "see https://github.com/posit-dev/py-shinywidgets/issues/332). "
    "Upgrade plotly (`pip install -U plotly`), or pin shinywidgets to 0.8.2 "
    "to keep using an older plotly."
)


def unsupported_plotly_version(w: Widget) -> Optional[Version]:
    """
    The plotly version, if `w` is a plotly widget and that version is too old
    to render (< 5.12, the first release whose FigureWidget
    frontend supports ipywidgets 8); otherwise None.
    """
    if not any(widget_pkg(cls) == "plotly" for cls in type(w).__mro__):
        return None
    version = _plotly_version()
    if version is not None and version < Version("5.12"):
        return version
    return None


def _plotly_version() -> Optional[Version]:
    """
    The version of the imported plotly, or of the installed one if that can't be
    determined.

    The imported module is the one that renders, and it isn't necessarily the
    one whose metadata is installed (e.g., a source checkout on `PYTHONPATH`
    shadowing an installed wheel).
    """
    versions: List[Optional[str]] = []
    try:
        import plotly

        versions.append(getattr(plotly, "__version__", None))
    except Exception:
        pass
    try:
        versions.append(package_version("plotly"))
    except PackageNotFoundError:
        pass

    for version in versions:
        if not version:
            continue
        try:
            return Version(version)
        except Exception:
            continue

    return None


def retire_unused_widget(w: Widget) -> None:
    # An inert comm stops Widget.open() from serializing the widget (which would
    # construct a default Layout widget that also needs a session)
    w.comm = OrphanedShinyComm(uuid4().hex)
    # Assigning a comm registers the widget instance; nothing will ever close it
    del WIDGET_INSTANCE_MAP[w.model_id]


def own_lonboard_controls(w: Widget) -> None:
    """
    Give a lonboard `Map` its own copies of `Map`'s shared default controls.

    Those controls are constructed once (when lonboard is imported) and shared by
    every Map, so they can't belong to this session. This runs before the Map's
    initial state is serialized, so the browser never sees the shared ones.
    """
    from lonboard import Map  # pyright: ignore[reportMissingImports]

    if not isinstance(w, Map):
        return
    # pyright can't narrow via isinstance() when lonboard isn't installed
    # (e.g., Python 3.15)
    shared = Map.class_traits()["controls"].default()
    if any(c in shared for c in w.controls):  # pyright: ignore[reportAttributeAccessIssue]
        w.controls = tuple(  # pyright: ignore[reportAttributeAccessIssue]
            copy_lonboard_control(c) if c in shared else c
            for c in w.controls  # pyright: ignore[reportAttributeAccessIssue]
        )


def copy_lonboard_control(control: Widget) -> Widget:
    names = [k for k in control.trait_names(sync=True) if not k.startswith("_")]
    return type(control)(**{k: getattr(control, k) for k in names})


@contextmanager
def session_lifetime() -> Iterator[None]:
    """
    Give widgets constructed inside this block the lifetime of the Shiny session
    rather than of the current render.

    Widgets constructed while an output renders are closed when that render is
    invalidated. Construct a widget inside `session_lifetime()` when you intend to
    display it again in a later render (for example, one cached widget per dataset).
    Exiting the block closes nothing; session widgets are closed when the session ends.

    A background task started during a render keeps that render's lifetime: if
    the task is meant to outlive its render (for example, one streaming updates
    into a map), construct its widgets inside `session_lifetime()`, or they are
    closed when the render that started the task is invalidated.
    """
    if get_current_session() is None:
        raise RuntimeError("session_lifetime() requires an active Shiny session")
    with WidgetRenderContext.suspended():
        yield


# Use WeakSet() over Set() so that the session can be garbage collected
SESSIONS: WeakSet[Session] = WeakSet()

# Widgets constructed during a render, keyed by that render's Context id. Closed
# when the Context is invalidated (see close_render_widgets).
RENDER_OWNED_WIDGETS: dict[int, list[Widget]] = {}

# Render-owned widgets a live widget in this session still referenced the last
# time their render ended, keyed by session id. Re-checked at the session's next
# render invalidation (see close_render_widgets) and closed once nothing in the
# session references them anymore.
KEPT_WIDGETS: dict[str, list[Widget]] = {}


def close_render_widgets(session: Session, widgets: list[Widget]) -> None:
    """
    Close the widgets a retired render constructed, except any that a live widget
    in this session still references (e.g. a Layout first materialized while
    serializing a session-owned widget). Those are kept and re-checked the next
    time a render in this session is invalidated, rather than skipped forever.
    """
    widgets = KEPT_WIDGETS.pop(session.id, []) + widgets
    closing = {id(w) for w in widgets}
    # Root the walk at this session's own live widgets, not every widget in the
    # process: a cross-session reference shouldn't keep a widget alive, and on a
    # server with many sessions, walking only this session's widgets keeps the
    # sweep's cost independent of how many other sessions are open.
    roots = (
        WIDGET_INSTANCE_MAP.get(wid)
        for wid in SESSION_WIDGET_ID_MAP.get(session.id, ())
    )
    keep = referenced_widgets(
        w for w in roots if w is not None and id(w) not in closing
    )
    kept: list[Widget] = []
    for w in widgets:
        if is_closed_widget(w):  # already closed (e.g. by this session ending)
            continue
        if id(w) in keep:
            kept.append(w)
            continue
        close_widget(w)
    if kept:
        KEPT_WIDGETS[session.id] = kept


def close_widget(w: Widget) -> None:
    """Close a widget, the same way whether its render was invalidated or its session ended."""
    model_id = w.model_id
    w.close()
    # By closing the widget, we also close the comm, which sets w.comm to
    # None. Unfortunately, the w.model_id property looks up w.comm.comm_id
    # at runtime, and some packages like ipyleaflet want to use this id
    # to manage references between widgets.
    w.comm = OrphanedShinyComm(model_id)
    # Assigning a comm has the side-effect of adding back a reference to
    # the widget instance, so remove it again
    if WIDGET_INSTANCE_MAP.get(model_id) is w:
        del WIDGET_INSTANCE_MAP[model_id]


def close_comm_on_close(w: Widget) -> None:
    """
    Make a widget's close() also close its comm.

    k3d's Plot overrides close() (to clear the ipywidgets Outputs it's displayed
    in) without calling Widget.close(), so its comm never closes: every re-render
    would leave the old plot's comm registered here and its model in the browser.
    Widget.close() is a no-op once the comm is gone, so this is safe for widgets
    whose close() already closes it.
    """
    close = w.close

    def close_with_comm() -> None:
        close()
        Widget.close(w)

    # Assigning to a method isn't expressible to the type checker, but patching
    # the instance is the point (we don't control k3d's class)
    w.close = close_with_comm  # type: ignore[method-assign]


def walk_widget_tree(
    roots: Iterable[object], prune: Callable[[Widget], bool] | None = None
) -> Iterator[Widget]:
    """
    Yield every widget reachable from `roots` through synced traits.

    Recurses into traits that have a `to_json` serializer (this is how
    `children`/`layout`/`style` etc. are tagged) plus dicts/lists/tuples wrapping
    those -- the same shape ipywidgets uses to serialize a widget tree to the
    client. Other traits can't carry a widget reference across the wire, so
    skipping them also avoids walking large opaque payloads like GeoJSON `data`
    or Altair specs that can't hold widgets anyway.

    A trait that hasn't been read yet is followed only if its static default is
    a widget (see `synced_trait_values`), so a widget a class pins as a default
    is found even before it's materialized.

    If `prune(w)` is true, `w` is still yielded but its traits aren't followed.
    """
    visited: set[int] = set()
    pending: list[object] = list(roots)
    while pending:
        item = pending.pop()
        if not isinstance(item, (Widget, dict, list, tuple)) or id(item) in visited:
            continue
        visited.add(id(item))
        if isinstance(item, Widget):
            yield item
            if prune is None or not prune(item):
                pending.extend(synced_trait_values(item))
        elif isinstance(item, dict):
            pending.extend(cast(dict[object, object], item).values())
        else:
            pending.extend(cast("list[object] | tuple[object, ...]", item))


def synced_trait_values(w: Widget) -> Iterator[object]:
    """
    Yield the values of `w`'s synced traits that can carry widget references
    (those with a `to_json` serializer).

    A trait that hasn't been read yet yields its default only if that default is
    already a widget. Dynamic defaults (e.g. the Layout/Style a widget builds on
    first access) are never evaluated here, since that would construct widgets as
    a side effect of walking.
    """
    for name in w.keys:
        if w.trait_metadata(name, "to_json") is None:
            continue
        if w.trait_has_value(name):
            yield getattr(w, name)
        else:
            default = w.traits()[name].default_value
            if isinstance(default, Widget):
                yield default


def direct_widget_references(w: Widget) -> Iterator[Widget]:
    """
    Yield the widgets `w` references directly, descending through dicts, lists and
    tuples but not into the widgets it yields.
    """
    visited: set[int] = set()
    pending: list[object] = list(synced_trait_values(w))
    while pending:
        item = pending.pop()
        if id(item) in visited:
            continue
        if isinstance(item, Widget):
            visited.add(id(item))
            yield item
        elif isinstance(item, dict):
            visited.add(id(item))
            pending.extend(cast(dict[object, object], item).values())
        elif isinstance(item, (list, tuple)):
            visited.add(id(item))
            pending.extend(cast("list[object] | tuple[object, ...]", item))


def referenced_widgets(roots: Iterable[Widget]) -> set[int]:
    """ids of every widget reachable from `roots` through materialized synced traits."""
    return {id(w) for w in walk_widget_tree(roots)}


def foreign_or_closed_widget(widget: Widget, session: Session) -> Widget | None:
    """
    Find the first widget in `widget`'s tree (itself, or any descendant reachable
    the same way `referenced_widgets` walks for the cleanup sweep) that doesn't
    belong to `session` or has already been closed.

    `session` must already be normalized to its root scope, matching how
    SESSION_WIDGET_ID_MAP is keyed. Returns None if the whole tree is
    displayable in this session.
    """
    own_ids = set(SESSION_WIDGET_ID_MAP.get(session.id, ()))
    for w in walk_widget_tree([widget]):
        if is_closed_widget(w) or w._model_id not in own_ids:
            return w
    return None


# One comm manager per session (keyed by session id), so a client can only reach
# its own session's widgets.
COMM_MANAGERS: dict[str, ShinyCommManager] = {}


def _decode_comm_buffers(msg: dict[str, Any]) -> dict[str, Any]:
    buffers = msg.get("buffers")
    if not buffers:
        return msg

    decoded_buffers = []
    for buf in buffers:
        if isinstance(buf, str):
            decoded_buffers.append(memoryview(b64decode(buf)))
        else:
            decoded_buffers.append(buf)

    msg["buffers"] = decoded_buffers
    return msg


# Dictionary mapping session id to widget ids
# The key is the session id, and the value is a list of widget ids
SESSION_WIDGET_ID_MAP: dict[str, list[str]] = {}

# --------------------------------------
# Reactivity
# --------------------------------------


def reactive_read(widget: Widget, names: Union[str, Sequence[str]]) -> Any:
    """
    Reactively read a widget trait.

    Takes a reactive dependency on the given trait(s), so the calling reactive context
    (e.g., a ``@reactive.Calc``, ``@reactive.Effect``, or render function) is
    invalidated whenever the trait's value changes (e.g., in response to user
    interaction with the widget in the browser).

    Parameters
    ----------
    widget
        The widget to read from (often obtained via the ``.widget`` attribute of a
        shinywidgets render decorator).
    names
        A trait name, or a sequence of trait names, to read.

    Returns
    -------
    :
        The trait's current value, or a tuple of values if `names` is a sequence.

    Examples
    --------
    ```python
    from shiny import reactive
    from shinywidgets import reactive_read, render_widget
    import ipyleaflet


    @render_widget
    def map():
        return ipyleaflet.Map(center=(51.5, -0.09), zoom=4)


    @reactive.Effect
    def _():
        # Re-runs whenever the map's zoom level changes
        print(reactive_read(map.widget, "zoom"))
    ```
    """
    reactive_depend(widget, names)
    if isinstance(names, str):
        return getattr(widget, names)
    else:
        return tuple(getattr(widget, name) for name in names)


def reactive_depend(
    widget: Widget,
    names: Union[str, Sequence[str]],
    type: str = "change",
) -> None:
    """
    Take a reactive dependency on a widget trait
    """

    try:
        ctx = get_current_context()
    except RuntimeError:
        raise RuntimeError("reactive_read() must be called within a reactive context")

    if isinstance(names, str):
        names = [names]

    for name in names:
        if not widget.has_trait(name):
            raise ValueError(
                f"The '{name}' attribute of {widget.__class__.__name__} is not a "
                "widget trait, and so it's not possible to reactively read it. "
                "For a list of widget traits, call `.trait_names()` on the widget."
            )

    def invalidate(change: object):
        ctx.invalidate()

    widget.observe(invalidate, names, type)  # type: ignore

    def _():
        widget.unobserve(invalidate, names, type)  # type: ignore

    ctx.on_invalidate(_)


def register_widget(
    id: str, widget: Widget, session: Optional[Session] = None
) -> Widget:
    """
    Deprecated. Use ``@render_widget`` instead.

    Registers `widget` as the Shiny output with id `id` on the given `session` (the
    current session, if not specified), and returns the widget.
    """
    if session is None:
        session = require_active_session(session)

    w = as_widget(widget)

    @session.output(id=id)
    @render_widget
    def _():
        return w

    return w


# It doesn't, at the moment, seem feasible to establish a comm with statically rendered widgets,
# and partially for this reason, it may not be sensible to provide an input-like API for them.

# def input_ipywidget(id: str, widget: object, rate_policy: Literal["debounce", "throttle"]="debounce", rate_policy_delay=200) -> Tag:
#     if not isinstance(widget, Widget):
#         raise TypeError("widget must be a Widget")
#     if not hasattr(widget, "value"):
#         # ipy.Button() don't inherently have value, but we create one that acts like actionButton()
#         if 'Button' != widget.__class__.__name__:
#           raise RuntimeError(
#               "widget must have a value property to be treated as an input. "
#               + "Do you want to render this widget as an output (i.e., output_widget())?"
#           )
#     return tags.div(
#         widget,
#         dependencies._core(),
#         dependencies._input_binding(),
#         id=id,
#         class_="shiny-ipywidget-input",
#         data_rate_policy=rate_policy,
#         data_rate_delay=rate_policy_delay,
#     )
#
# # https://ipywidgets.readthedocs.io/en/7.6.5/examples/Widget%20Low%20Level.html#Serialization-of-widget-attributes
# @input_handlers.add("shinywidgets.ipywidget")
# def _(value: int, session: Session, name: str):
#     return widget_serialization["from_json"](value, dict())
