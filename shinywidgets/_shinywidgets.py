from __future__ import annotations

import copy
import json
import os
from base64 import b64decode
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Optional, Sequence, Union, cast

import ipywidgets

from ._render_widget import render_widget

__protocol_version__ = ipywidgets._version.__protocol_version__
DOMWidget = ipywidgets.widgets.DOMWidget
Layout = ipywidgets.widgets.Layout
Widget = ipywidgets.widgets.Widget
_remove_buffers = ipywidgets.widgets.widget._remove_buffers
from htmltools import TagList
from shiny import Session, reactive
from shiny.http_staticfiles import StaticFiles
from shiny.reactive._core import (
    get_current_context,  # pyright: ignore[reportPrivateImportUsage]
)
from shiny.session import get_current_session, require_active_session, session_context

from ._as_widget import as_widget
from ._cdn import SHINYWIDGETS_CDN_ONLY, SHINYWIDGETS_EXTENSION_WARNING
from ._comm import BufferType, PendingShinyComm, ShinyComm
from ._dependencies import require_dependency
from ._lifecycle import (
    Lifetime,
    SessionLifecycle,
    get_lifecycle,
    selected_lifetime,
)
from ._render_widget_base import WidgetRenderContext
from ._utils import package_dir

__all__ = (
    "register_widget",
    "reactive_read",
)

if TYPE_CHECKING:
    from typing import TypeGuard

    from traitlets.traitlets import Instance


# --------------------------------------------------------------------------------------------
# When a widget is initialized, also initialize a communication channel (via the Shiny
# session). Note that when the comm is initialized, it also sends the initial state of
# the widget.
# --------------------------------------------------------------------------------------------
def init_shiny_widget(w: Widget):
    session = get_current_session()
    if session is None:
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

    lifecycle = get_lifecycle(session)
    wire_session(session, lifecycle)

    # Make sure window.require() calls made by 3rd party widgets
    # (via handle_comm_open() -> new_model() -> loadClass() -> requireLoader())
    # actually point to directories served locally by shiny
    if SHINYWIDGETS_CDN_ONLY:
        widget_dep = None
    else:
        widget_dep = require_dependency(w, session, SHINYWIDGETS_EXTENSION_WARNING)

    record = lifecycle.register(w, current_lifetime(lifecycle))
    id = record.model_id

    # Since the actual ShinyComm() is initialized _after_ the Widget is initialized,
    # and Widget.__init__() includes a call to Widget.open() which opens an unnecessary
    # comm, we just set the comm to a dummy comm for now (to avoid unnecessary work).
    # Unlike OrphanedShinyComm, closing this comm is observable, so that closing the
    # widget before initialization cancels the scheduled open (instead of letting it
    # reopen the closed widget).
    w.comm = PendingShinyComm(id, notify_closed=lambda: lifecycle.close_record(id))

    # Schedule the opening of the comm to happen sometime after this init function.
    # This is important for widgets like plotly that do additional initialization that
    # is required to get a valid widget state.
    @reactive.effect(priority=99999)
    def _open_shiny_comm():
        if record.state == "closed":
            _open_shiny_comm.destroy()
            return

        record.state = "opening"

        # Call _repr_mimebundle_() before get_state() since it may modify the widget
        # in an important way (unfortunately, it does for plotly)
        # # https://github.com/plotly/plotly.py/blob/0089f32/packages/python/plotly/plotly/basewidget.py#L734-L738
        if hasattr(w, "_repr_mimebundle_") and callable(w._repr_mimebundle_):
            w._repr_mimebundle_()

        # Now, get the state
        state, buffer_paths, buffers = _remove_buffers(w.get_state())

        # Initialize the comm -- this sends widget state to the frontend
        with widget_comm_patch():
            w.comm = ShinyComm(
                comm_id=id,
                comm_manager=lifecycle.comm_manager,
                target_name="jupyter.widget",
                session=session,
                data={"state": state, "buffer_paths": buffer_paths},
                buffers=cast(BufferType, buffers),
                # TODO: should this be hard-coded?
                metadata={"version": __protocol_version__},
                html_deps=session._process_ui(TagList(widget_dep))["deps"],
                on_closed=lambda: lifecycle.close_record(id),
            )

        record.state = "open"
        _open_shiny_comm.destroy()

    lifecycle.set_initializer(record, _open_shiny_comm.destroy)

    # Some widget's JS make external requests for static files (e.g.,
    # ipyleaflet markers) under this resource path. Note that this assumes that
    # we're setting the data-base-url attribute on the <body> (which we should
    # be doing on load in js/src/output.ts)
    # https://github.com/jupyter-widgets/widget-cookiecutter/blob/9694718/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js#L8
    if widget_dep and widget_dep.source:
        src_dir = widget_dep.source.get("subdir", "")
        if src_dir:
            session.app._dependency_handler.mount(
                f"/nbextensions/{widget_dep.name}",
                StaticFiles(directory=src_dir),
                name=f"{widget_dep.name}-nbextension-static-resources",
            )


def current_lifetime(lifecycle: SessionLifecycle) -> Lifetime:
    """
    The lifetime that widgets constructed right now belong to.

    Selection precedence is an explicit `session_lifetime()` selection, then the
    current widget render, then the root session. (Render lifetimes are captured
    in `_render_widget_base.WidgetRenderContext`; explicit selection is a
    `_lifecycle` ContextVar.)
    """
    lifetime = selected_lifetime.get()
    if lifetime is not None:
        return lifetime
    render_lifetime = WidgetRenderContext.get_render_lifetime()
    if render_lifetime is not None:
        return render_lifetime
    return lifecycle.session_lifetime


def wire_session(session: Session, lifecycle: SessionLifecycle) -> None:
    """
    Set up session-level widget machinery (static mounts, client->server message
    routing) the first time a session constructs a widget.
    """
    if lifecycle.wired:
        return
    lifecycle.wired = True

    # Somewhere inside ipywidgets, it makes requests for static files
    # under the publicPath set by the webpack.config.js file.
    session.app._dependency_handler.mount(
        "/dist/",
        StaticFiles(directory=os.path.join(package_dir("shinywidgets"), "static")),
        name="shinywidgets-static-resources",
    )

    with session_context(session):
        # Handle messages from the client. Note that widgets like qgrid send client->server messages
        # to figure out things like what filter to be shown in the table.
        @reactive.effect
        @reactive.event(session.input.shinywidgets_comm_send)
        def _():
            msg_txt = session.input.shinywidgets_comm_send()
            msg = _decode_comm_buffers(json.loads(msg_txt))
            comm_id = msg["content"]["comm_id"]
            comm = lifecycle.comm_manager.comms.get(comm_id)
            if comm is not None:
                comm.handle_msg(msg)


# TODO: can we restore the widget constructor in a sensible way?
Widget.on_widget_constructed(init_shiny_widget)  # type: ignore


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


# --------------------------------------
# Reactivity
# --------------------------------------


def reactive_read(widget: Widget, names: Union[str, Sequence[str]]) -> Any:
    """
    Reactively read a widget trait
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
    Deprecated. Use @render_widget instead.
    """
    if session is None:
        session = require_active_session(session)

    w = as_widget(widget)

    @session.output(id=id)
    @render_widget
    def _():
        return w

    return w


# Previous versions of ipywidgets (< 8.0.5) had
#   `Widget.comm = Instance('ipykernel.comm.Comm')`
# which meant we'd get a runtime error when setting `Widget.comm = ShinyComm()`.
# In more recent versions, this is no longer necessary since they've (correctly)
# changed comm from an Instance() to Any().
# https://github.com/jupyter-widgets/ipywidgets/pull/3533/files#diff-522bb5e7695975cba0199c6a3d6df5be827035f4dc18ed6da22ac216b5615c77R482
@contextmanager
def widget_comm_patch():
    if not is_traitlet_instance(Widget.comm):
        yield
        return

    comm_klass = copy.copy(Widget.comm.klass)
    Widget.comm.klass = object

    yield

    Widget.comm.klass = comm_klass


def is_traitlet_instance(x: object) -> "TypeGuard[Instance[Any]]":
    try:
        from traitlets.traitlets import Instance
    except ImportError:
        return False
    return isinstance(x, Instance)


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
