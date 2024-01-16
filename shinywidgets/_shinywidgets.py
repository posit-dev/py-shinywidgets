from __future__ import annotations

import copy
import importlib
import json
import os
import tempfile
import warnings
from typing import Any, Optional, Sequence, Tuple, Union, cast
from uuid import uuid4
from weakref import WeakSet

import ipywidgets  # pyright: ignore[reportMissingTypeStubs]

from ._render_widget import render_widget

__protocol_version__ = ipywidgets._version.__protocol_version__
DOMWidget = ipywidgets.widgets.DOMWidget
Layout = ipywidgets.widgets.Layout
Widget = ipywidgets.widgets.Widget
_remove_buffers = ipywidgets.widgets.widget._remove_buffers  # pyright: ignore
from htmltools import TagList
from shiny import Session, reactive
from shiny.http_staticfiles import StaticFiles
from shiny.reactive._core import get_current_context
from shiny.session import get_current_session, require_active_session

from ._as_widget import as_widget
from ._cdn import SHINYWIDGETS_CDN_ONLY, SHINYWIDGETS_EXTENSION_WARNING
from ._comm import BufferType, ShinyComm, ShinyCommManager
from ._dependencies import require_dependency, widget_pkg

__all__ = (
    "register_widget",
    "reactive_read",
)


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
    # Break out of any module-specific session. Otherwise, input.shinywidgets_comm_send
    # will be some module-specific copy.
    while hasattr(session, "_parent"):
        session = cast(Session, session._parent)  # pyright: ignore

    # Previous versions of ipywidgets (< 8.0.5) had
    #   `Widget.comm = Instance('ipykernel.comm.Comm')`
    # which meant we'd get a runtime error when setting `Widget.comm = ShinyComm()`.
    # In more recent versions, this is no longer necessary since they've (correctly)
    # changed comm from an Instance() to Any().
    # https://github.com/jupyter-widgets/ipywidgets/pull/3533/files#diff-522bb5e7695975cba0199c6a3d6df5be827035f4dc18ed6da22ac216b5615c77R482
    old_comm_klass = None
    if is_instance_of_class(Widget.comm, "Instance", "traitlets.traitlets"):  # type: ignore
        old_comm_klass = copy.copy(Widget.comm.klass)  # type: ignore
        Widget.comm.klass = object  # type: ignore

    # Get the initial state of the widget
    state, buffer_paths, buffers = _remove_buffers(w.get_state())  # type: ignore

    # Make sure window.require() calls made by 3rd party widgets
    # (via handle_comm_open() -> new_model() -> loadClass() -> requireLoader())
    # actually point to directories served locally by shiny
    if SHINYWIDGETS_CDN_ONLY:
        widget_dep = None
    else:
        widget_dep = require_dependency(w, session, SHINYWIDGETS_EXTENSION_WARNING)

    # By the time we get here, the user has already had an opportunity to specify a model_id,
    # so it isn't yet populated, generate a random one so we can assign the same id to the comm
    if getattr(w, "_model_id", None) is None:
        w._model_id = uuid4().hex

    # Initialize the comm...this will also send the initial state of the widget
    w.comm = ShinyComm(
        comm_id=w._model_id,  # pyright: ignore
        comm_manager=COMM_MANAGER,
        target_name="jupyter.widgets",
        data={"state": state, "buffer_paths": buffer_paths},
        buffers=cast(BufferType, buffers),
        # TODO: should this be hard-coded?
        metadata={"version": __protocol_version__},
        html_deps=session._process_ui(TagList(widget_dep))["deps"],
    )

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

    # everything after this point should be done once per session
    if session in SESSIONS:
        return
    SESSIONS.add(session)  # type: ignore

    # Somewhere inside ipywidgets, it makes requests for static files
    # under the publicPath set by the webpack.config.js file.
    session.app._dependency_handler.mount(
        "/dist/",
        StaticFiles(directory=os.path.join(package_dir("shinywidgets"), "static")),
        name="shinywidgets-static-resources",
    )

    # Handle messages from the client. Note that widgets like qgrid send client->server messages
    # to figure out things like what filter to be shown in the table.
    @reactive.Effect
    @reactive.event(session.input.shinywidgets_comm_send)
    def _():
        msg_txt = session.input.shinywidgets_comm_send()
        msg = json.loads(msg_txt)
        comm_id = msg["content"]["comm_id"]
        comm: ShinyComm = COMM_MANAGER.comms[comm_id]
        comm.handle_msg(msg)

    def _restore_state():
        if old_comm_klass is not None:
            Widget.comm.klass = old_comm_klass  # type: ignore
        SESSIONS.remove(session)  # type: ignore

    session.on_ended(_restore_state)


# TODO: can we restore the widget constructor in a sensible way?
Widget.on_widget_constructed(init_shiny_widget)  # type: ignore

# Use WeakSet() over Set() so that the session can be garbage collected
SESSIONS = WeakSet()  # type: ignore
COMM_MANAGER = ShinyCommManager()


# --------------------------------------
# Reactivity
# --------------------------------------


# TODO-barret; Make method on RenderWidget base
def reactive_read(widget: Widget, names: Union[str, Sequence[str]]) -> Any:
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
    Reactively read a Widget's trait(s)
    """

    try:
        ctx = get_current_context()
    except RuntimeError:
        raise RuntimeError("reactive_read() must be called within a reactive context")

    if isinstance(names, str):
        names = [names]

    for name in names:
        if not widget.has_trait(name):  # pyright: ignore[reportUnknownMemberType]
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


# TODO-barret; Proposal: Remove `register_widget()` in favor of `@render_widget`
def register_widget(
    id: str, widget: Widget, session: Optional[Session] = None
) -> Widget:
    if session is None:
        session = require_active_session(session)

    w = as_widget(widget)

    @session.output(id=id)
    @render_widget
    def _():
        return w

    return w


def set_layout_defaults(widget: Widget) -> Tuple[Widget, bool]:
    # If we detect a user specified height on the widget, then don't
    # do filling layout (akin to the behavior of output_widget(height=...))
    fill = True

    if not isinstance(widget, DOMWidget):
        return (widget, fill)

    # Do nothing for "input-like" widgets (e.g., ipywidgets.IntSlider())
    if getattr(widget, "_model_module", None) == "@jupyter-widgets/controls":
        return (widget, False)

    layout = widget.layout  # type: ignore

    # If the ipywidget Layout() height is set to something other than "auto", then
    # don't do filling layout https://ipywidgets.readthedocs.io/en/stable/examples/Widget%20Layout.html
    if isinstance(layout, Layout):
        if layout.height is not None and layout.height != "auto":  # type: ignore
            fill = False

    pkg = widget_pkg(widget)

    # Plotly provides it's own layout API (which isn't a subclass of ipywidgets.Layout)
    if pkg == "plotly":
        from plotly.graph_objs import Layout as PlotlyLayout  # pyright: ignore

        if isinstance(layout, PlotlyLayout):
            if layout.height is not None:  # pyright: ignore[reportUnknownMemberType]
                fill = False
            # Default margins are also way too big
            layout.template.layout.margin = dict(  # pyright: ignore
                l=16, t=32, r=16, b=16
            )
            # Unfortunately, plotly doesn't want to respect the top margin template,
            # so change that 60px default to 32px
            if layout.margin["t"] == 60:  # pyright: ignore
                layout.margin["t"] = 32  # pyright: ignore

    widget.layout = layout

    # altair, confusingly, isn't setup to fill it's Layout() container by default. I
    # can't imagine a situation where you'd actually want it to _not_ fill the parent
    # container since it'll be contained within the Layout() container, which has a
    # full-fledged sizing API.
    if pkg == "altair":
        import altair as alt

        # Since as_widget() has already happened, we only need to handle JupyterChart
        if isinstance(widget, alt.JupyterChart):
            if isinstance(
                widget.chart,  # pyright: ignore[reportUnknownMemberType]
                alt.ConcatChart,
            ):
                # Throw warning to use ui.layout_column_wrap() instead
                warnings.warn(
                    "Consider using shiny.ui.layout_column_wrap() instead of alt.concat() "
                    "for multi-column layout (the latter doesn't support filling layout)."
                )
            else:
                widget.chart = widget.chart.properties(width="container", height="container")  # type: ignore

    return (widget, fill)


# similar to base::system.file()
def package_dir(package: str) -> str:
    with tempfile.TemporaryDirectory():
        pkg_file = importlib.import_module(".", package=package).__file__
        if pkg_file is None:
            raise ImportError(f"Couldn't load package {package}")
        return os.path.dirname(pkg_file)


def is_instance_of_class(
    x: object, class_name: str, module_name: Optional[str] = None
) -> bool:
    typ = type(x)
    res = typ.__name__ == class_name
    if module_name is None:
        return res
    else:
        return res and typ.__module__ == module_name


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
