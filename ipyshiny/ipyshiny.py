from htmltools import tags, Tag, TagList, HTMLDependency
import inspect
from ipywidgets.widgets import DOMWidget
from ipywidgets.embed import embed_data, dependency_state
from ipywidgets._version import __html_manager_version__
import json
import re
from shiny.render import RenderFunction, RenderFunctionAsync
from shiny.utils import run_coro_sync, wrap_async, process_deps
from typing import List, Dict, Callable, Awaitable, Union, Any, cast
from .__init__ import __version__

html_manager_version = re.sub("^\\D*", "", __html_manager_version__)

__all__ = [
  "output_ipywidget",
  "render_ipywidget",
  "input_ipywidget",
]


def output_ipywidget(id: str) -> Tag:
    return tags.div(
        _ipywidget_embed_deps(),
        _ipywidget_output_dep(),
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
        ui = _get_ipywidget_html(widget)
        return process_deps(ui, self._session)


class IPyWidgetAsync(RenderFunctionAsync):
    def __init__(self, fn: IPyWidgetRenderFuncAsync) -> None:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError("IPyWidgetAsync requires an async function")

        super().__init__(lambda: None)
        self._fn: IPyWidgetRenderFuncAsync = fn

    async def __call__(self) -> object:
        return await self.run()


def render_ipywidget():
    def wrapper(fn: Union[IPyWidgetRenderFunc, IPyWidgetRenderFuncAsync]) -> DOMWidget:
        if inspect.iscoroutinefunction(fn):
            fn = cast(IPyWidgetRenderFuncAsync, fn)
            return IPyWidgetAsync(fn)
        else:
            fn = cast(IPyWidgetRenderFunc, fn)
            return IPyWidget(fn)

    return wrapper

def input_ipywidget(id: str, widget: object) -> Tag:
    if not isinstance(widget, DOMWidget):
        raise TypeError("widget must be a DOMWidget")
    if not hasattr(widget, "value"):
        raise RuntimeError(
            "widget must have a value property to be treated as an input. "
            + "Do you want to render this widget as an output (i.e., output_ipywidget())?"
        )
    return tags.div(
        widget,
        _ipywidget_embed_deps(),
        _ipywidget_input_dep(),
        id=id,
        class_="shiny-ipywidget-input",
    )


# TODO: create these automatically when 
def _ipywidget_embed_deps() -> List[HTMLDependency]:
    return [
        HTMLDependency(
            name="requirejs",
            version="2.3.4",
            source={"package": "ipyshiny", "subdir": "static"},
            script={"src": "require.min.js"},
        ),
        HTMLDependency(
            name="ipywidget-libembed-amd",
            version=html_manager_version,
            source={"package": "ipyshiny", "subdir": "static"},
            script={"src": "libembed-amd.js"},
        ),
    ]


def _ipywidget_output_dep() -> HTMLDependency:
    return HTMLDependency(
        name="ipywidget-output-binding",
        version=__version__,
        source={"package": "ipyshiny", "subdir": "static"},
        script={"src": "output.js"},
    )


def _ipywidget_input_dep() -> HTMLDependency:
    return HTMLDependency(
        name="ipywidget-input-binding",
        version=__version__,
        source={"package": "ipyshiny", "subdir": "static"},
        script={"src": "input.js"},
    )


# TODO: allow a way to customize the CDN
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
