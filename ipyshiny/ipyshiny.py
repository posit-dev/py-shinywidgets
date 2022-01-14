import inspect
import json
from typing import Dict, Callable, Awaitable, Literal, Union, Any, cast

from htmltools import tags, Tag, TagList
from ipywidgets import widget_serialization
from ipywidgets.widgets import DOMWidget
from ipywidgets.embed import embed_data, dependency_state
from shiny import ShinySession
from shiny.input_handlers import input_handlers
from shiny.render import RenderFunction, RenderFunctionAsync
from shiny.shinysession import _process_deps
from shiny.utils import run_coro_sync, wrap_async

from . import dependencies

__all__ = [
  "output_ipywidget",
  "render_ipywidget",
  "input_ipywidget",
]


def output_ipywidget(id: str) -> Tag:
    return tags.div(
        dependencies._core(),
        dependencies._output_binding(),
        id=id,
        class_="shiny-ipywidget-output",
    )


IPyWidgetRenderFunc = Callable[[], DOMWidget]
IPyWidgetRenderFuncAsync = Callable[[], Awaitable[DOMWidget]]


class IPyWidget(RenderFunction):
    def __init__(self, fn: IPyWidgetRenderFunc) -> None:
        self._fn: IPyWidgetRenderFuncAsync = wrap_async(fn)

    def __call__(self) -> object:
        return run_coro_sync(self.run())

    async def run(self) -> object:
        widget: DOMWidget = await self._fn()
        widget_pkg = widget.__module__.split(".")[0]
        deps = dependencies._require_deps(widget_pkg)
        return _process_deps(TagList(deps, widget), self._session)


class IPyWidgetAsync(RenderFunctionAsync):
    def __init__(self, fn: IPyWidgetRenderFuncAsync) -> None:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError("IPyWidgetAsync requires an async function")

        super().__init__(lambda: None)
        self._fn: IPyWidgetRenderFuncAsync = fn

    async def __call__(self) -> object:
        return await self.run()

# TODO: could this just be a simple wrapper around render_ui()?
def render_ipywidget():
    def wrapper(fn: Union[IPyWidgetRenderFunc, IPyWidgetRenderFuncAsync]) -> DOMWidget:
        if inspect.iscoroutinefunction(fn):
            fn = cast(IPyWidgetRenderFuncAsync, fn)
            return IPyWidgetAsync(fn)
        else:
            fn = cast(IPyWidgetRenderFunc, fn)
            return IPyWidget(fn)

    return wrapper

def input_ipywidget(id: str, widget: object, rate_policy: Literal["debounce", "throttle"]="debounce", rate_policy_delay=200) -> Tag:
    if not isinstance(widget, DOMWidget):
        raise TypeError("widget must be a DOMWidget")
    if not hasattr(widget, "value"):
        # ipy.Button() don't inherently have value, but we create one that acts like actionButton() 
        if 'Button' != widget.__class__.__name__:
          raise RuntimeError(
              "widget must have a value property to be treated as an input. "
              + "Do you want to render this widget as an output (i.e., output_ipywidget())?"
          )
    return tags.div(
        widget,
        dependencies._core(),
        dependencies._input_binding(),
        id=id,
        class_="shiny-ipywidget-input",
        data_rate_policy=rate_policy,
        data_rate_delay=rate_policy_delay,
    )


def _get_ipywidget_html(widget: DOMWidget) -> TagList:
    dat: Dict[str, Any] = embed_data(
        views=[widget], state=dependency_state(widgets=[widget])
    )
    return TagList(
        tags.script(
            json.dumps(dat["manager_state"]),
            type="application/vnd.jupyter.widget-state+json",
            data_jupyter_widgets_cdn_only="",
        ),
        tags.script(
            [json.dumps(view) for view in dat["view_specs"]],
            type="application/vnd.jupyter.widget-view+json",
            data_jupyter_widgets_cdn_only="",
        ),
    )

setattr(DOMWidget, "tagify", _get_ipywidget_html)

# https://ipywidgets.readthedocs.io/en/7.6.5/examples/Widget%20Low%20Level.html#Serialization-of-widget-attributes


@input_handlers.add("ipyshiny.ipywidget")
def _(value: int, session: ShinySession, name: str):
  return widget_serialization["from_json"](value, dict())
