from __future__ import annotations

__all__ = ("output_widget", "render_widget", "reactive_read")

import copy
import inspect
import json
import os
from typing import Callable, Awaitable, Sequence, Union, cast, Any
from uuid import uuid4
from weakref import WeakSet

from ipywidgets.widgets.widget import Widget, _remove_buffers
from ipywidgets._version import __protocol_version__

from htmltools import tags, Tag, TagList, css
from htmltools._util import _package_dir
from shiny import event, reactive

from shiny.http_staticfiles import StaticFiles
from shiny.session import get_current_session
from shiny.render import RenderFunction, RenderFunctionAsync
from shiny._utils import run_coro_sync, wrap_async

from ._dependencies import *
from ._comm import ShinyComm, ShinyCommManager, BufferType


def output_widget(
    id: str, *, width: str = "100%", height: str = "400px", inline: bool = False
) -> Tag:
    # TODO: we should probably have a way to customize the container tag, like you can
    # in htmlwidgets
    return tags.div(
        *libembed_dependency(),
        output_binding_dependency(),
        id=id,
        class_="shiny-ipywidget-output",
        style=css(
            width=width, height=height, display="inline-block" if inline else None
        ),
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
            "ipyshiny requires that all ipywidgets be constructed within an active Shiny session"
        )

    # `Widget` has `comm = Instance('ipykernel.comm.Comm')` which means we'd get a
    # runtime error if we try to set this attribute to a different class, but
    # fortunately this hack provides a workaround.
    # TODO: find a better way to do this (maybe send a PR to ipywidgets?) or at least clean up after ourselves
    # https://github.com/jupyter-widgets/ipywidgets/blob/88cec8b/python/ipywidgets/ipywidgets/widgets/widget.py#L424
    old_comm_klass = copy.copy(Widget.comm.klass)  # type: ignore
    Widget.comm.klass = object  # type: ignore

    # Get the initial state of the widget
    state, buffer_paths, buffers = _remove_buffers(w.get_state())  # type: ignore

    # Make sure window.require() calls made by 3rd party widgets
    # (via handle_comm_open() -> new_model() -> loadClass() -> requireLoader())
    # actually point to directories served locally by shiny
    widget_dep = require_dependency(w, session)

    # By the time we get here, the user has already had an opportunity to specify a model_id,
    # so it isn't yet populated, generate a random one so we can assign the same id to the comm
    if getattr(w, "_model_id", None) is None:
        setattr(w, "_model_id", uuid4().hex)

    # Initialize the comm...this will also send the initial state of the widget
    w.comm = ShinyComm(
        comm_id=getattr(w, "_model_id"),
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
        session.app._dependency_handler.mount(
            f"/nbextensions/{widget_dep.name}",
            StaticFiles(directory=widget_dep.source["subdir"]),
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
        StaticFiles(directory=os.path.join(_package_dir("ipyshiny"), "static")),
        name="ipyshiny-static-resources",
    )

    # Handle messages from the client. Note that widgets like qgrid send client->server messages
    # to figure out things like what filter to be shown in the table.
    @reactive.Effect()
    @event(session.input["ipyshiny_comm_send"])
    def _():
        msg_txt = session.input["ipyshiny_comm_send"]()
        msg = json.loads(msg_txt)
        comm_id = msg["content"]["comm_id"]
        comm: ShinyComm = COMM_MANAGER.comms[comm_id]
        comm.handle_msg(msg)

    def _restore_state():
        Widget.comm.klass = old_comm_klass  # type: ignore
        SESSIONS.remove(session)  # type: ignore

    session.on_ended(_restore_state)


# TODO: can we restore the widget constructor in a sensible way?
Widget.on_widget_constructed(init_shiny_widget)  # type: ignore

# Use WeakSet() over Set() so that the session can be garbage collected
SESSIONS = WeakSet()  # type: ignore
COMM_MANAGER = ShinyCommManager()


# --------------------------------------------------------------------------------------------
# Implement @render_widget()
# TODO: shiny should probably make this simpler
# --------------------------------------------------------------------------------------------

IPyWidgetRenderFunc = Callable[[], Widget]
IPyWidgetRenderFuncAsync = Callable[[], Awaitable[Widget]]


class IPyWidget(RenderFunction):
    def __init__(self, fn: IPyWidgetRenderFunc) -> None:
        super().__init__(fn)
        self._fn: IPyWidgetRenderFuncAsync = wrap_async(fn)

    def __call__(self) -> object:
        return run_coro_sync(self.run())

    async def run(self) -> object:
        x = await self._fn()
        if x is None:
            return None
        widget = _as_widget(x)
        return {"model_id": widget.model_id}  # type: ignore


class IPyWidgetAsync(IPyWidget, RenderFunctionAsync):
    def __init__(self, fn: IPyWidgetRenderFuncAsync) -> None:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError("IPyWidgetAsync requires an async function")
        super().__init__(cast(IPyWidgetRenderFunc, fn))

    async def __call__(self) -> object:
        return await self.run()


def render_widget():
    def wrapper(fn: Union[IPyWidgetRenderFunc, IPyWidgetRenderFuncAsync]) -> IPyWidget:
        if inspect.iscoroutinefunction(fn):
            fn = cast(IPyWidgetRenderFuncAsync, fn)
            return IPyWidgetAsync(fn)
        else:
            fn = cast(IPyWidgetRenderFunc, fn)
            return IPyWidget(fn)

    return wrapper


# altair objects aren't directly renderable as an ipywidget,
# but we can still render them as an ipywidget via ipyvega
# TODO: we should probably do this for bokeh, pydeck, and probably others as well
def _as_widget(x: object) -> Widget:
    if widget_pkg(x) == "altair":
        try:
            import altair
            from vega.widget import VegaWidget

            x = cast(altair.Chart, x)
            x = VegaWidget(x.to_dict())  # type: ignore
        except ImportError:
            raise ImportError("ipyvega is required to render altair charts")
    elif widget_pkg(x) == "pydeck":
        import pydeck

        if isinstance(x, pydeck.Deck):
            from pydeck.widget import DeckGLWidget

            x_ = x.to_json()
            x = DeckGLWidget()
            x.json_input = x_

    if isinstance(x, Widget):
        return x
    else:
        raise TypeError(f"{x} is not a coerce-able to a ipywidget.Widget object")


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

    ctx = reactive.get_current_context()

    def invalidate(change: object):
        ctx.invalidate()

    widget.observe(invalidate, names, type)  # type: ignore

    def _():
        widget.unobserve(invalidate, names, type)  # type: ignore

    ctx.on_invalidate(_)


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
# @input_handlers.add("ipyshiny.ipywidget")
# def _(value: int, session: Session, name: str):
#     return widget_serialization["from_json"](value, dict())
