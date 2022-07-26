from __future__ import annotations

# TODO: export _as_widget()?
__all__ = ("output_widget", "register_widget", "render_widget", "reactive_read")

import copy
import inspect
import json
import os
from typing import Any, Awaitable, Callable, Optional, Sequence, Union, cast, overload
from uuid import uuid4
from weakref import WeakSet

from htmltools import Tag, TagList, css, tags
from htmltools._util import _package_dir
from ipywidgets._version import (
    __protocol_version__,  # pyright: ignore[reportUnknownVariableType]
)

from ipywidgets.widgets.widget import (
    Widget,
    _remove_buffers,  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]
)
from shiny import Session, event, reactive
from shiny._utils import run_coro_sync, wrap_async
from shiny.http_staticfiles import StaticFiles
from shiny.render import RenderFunction, RenderFunctionAsync
from shiny.session import get_current_session, require_active_session
from shiny.module import resolve_id

from ._comm import BufferType, ShinyComm, ShinyCommManager
from ._dependencies import (
    libembed_dependency,
    output_binding_dependency,
    require_dependency,
    widget_pkg,
)


def output_widget(
    id: str, *, width: Optional[str] = None, height: Optional[str] = None
) -> Tag:
    id = resolve_id(id)
    return tags.div(
        *libembed_dependency(),
        output_binding_dependency(),
        id=id,
        class_="shiny-ipywidget-output",
        style=css(width=width, height=height),
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
        session = session._parent

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
        StaticFiles(directory=os.path.join(_package_dir("shinywidgets"), "static")),
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


@overload
def render_widget(
    fn: Union[IPyWidgetRenderFunc, IPyWidgetRenderFuncAsync]
) -> IPyWidget:
    ...


@overload
def render_widget() -> Callable[
    [Union[IPyWidgetRenderFunc, IPyWidgetRenderFuncAsync]], IPyWidget
]:
    ...


def render_widget(
    fn: Optional[Union[IPyWidgetRenderFunc, IPyWidgetRenderFuncAsync]] = None
) -> Union[
    IPyWidget,
    Callable[[Union[IPyWidgetRenderFunc, IPyWidgetRenderFuncAsync]], IPyWidget],
]:
    def wrapper(fn: Union[IPyWidgetRenderFunc, IPyWidgetRenderFuncAsync]) -> IPyWidget:
        if inspect.iscoroutinefunction(fn):
            fn = cast(IPyWidgetRenderFuncAsync, fn)
            return IPyWidgetAsync(fn)
        else:
            fn = cast(IPyWidgetRenderFunc, fn)
            return IPyWidget(fn)

    if fn is None:
        return wrapper
    else:
        return wrapper(fn)


# altair/pydeck/bokeh objects aren't directly renderable as an ipywidget,
# but we can coerce them into one
def _as_widget(x: object) -> Widget:
    pkg = widget_pkg(x)
    if pkg == "altair" and not isinstance(x, Widget):
        try:
            import altair
            from vega.widget import VegaWidget

            x = cast(altair.Chart, x)
            x = VegaWidget(x.to_dict())  # type: ignore
        except ImportError:
            raise ImportError(
                "To render altair charts, the ipyvega package must be installed."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to coerce {x} into a VegaWidget: {e}")

    elif pkg == "pydeck" and not isinstance(x, Widget):
        try:
            from pydeck.widget import DeckGLWidget

            x = x.show()
        except Exception as e:
            raise RuntimeError(f"Failed to coerce {x} into a DeckGLWidget: {e}")

    elif pkg == "bokeh" and not isinstance(x, Widget):
        try:
            from jupyter_bokeh import BokehModel

            x = BokehModel(x)  # type: ignore
        except ImportError:
            raise ImportError(
                "To render bokeh charts, the jupyter_bokeh package must be installed."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to coerce {x} into a BokehModel: {e}")

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


def register_widget(
    id: str, widget: Widget, session: Optional[Session] = None
) -> Widget:
    if session is None:
        session = require_active_session(session)

    w = _as_widget(widget)

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
