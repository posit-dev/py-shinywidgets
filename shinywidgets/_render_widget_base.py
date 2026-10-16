from __future__ import annotations

import warnings
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Generic, Optional, Tuple, TypeVar, cast

from htmltools import Tag
from ipywidgets.widgets import DOMWidget, Layout, Widget
from shiny import req
from shiny.reactive import Context
from shiny.reactive._core import (
    get_current_context,  # pyright: ignore[reportPrivateImportUsage]
)
from shiny.render.renderer import Jsonifiable, Renderer, ValueFn
from shiny.session import get_current_session
from shiny.types import SilentCancelOutputException

from ._as_widget import as_widget
from ._dependencies import widget_pkg
from ._lifecycle import Lifetime, get_lifecycle
from ._output_widget import output_widget

__all__ = (
    "render_widget_base",
    "WidgetT",
    "ValueT",
)

# --------------------------------------------------------------------------------------------
# Implement @render_widget()
# --------------------------------------------------------------------------------------------

ValueT = TypeVar("ValueT", bound=object)
"""
The type of the value returned by the Shiny app render function
"""
WidgetT = TypeVar("WidgetT", bound=Widget)
"""
The type of the widget created from the renderer's ValueT
"""
T = TypeVar("T", bound=object)


class render_widget_base(Renderer[ValueT], Generic[ValueT, WidgetT]):
    """ """

    def auto_output_ui(self) -> Tag:
        return output_widget(
            self.output_id,
            width=self.width,
            height=self.height,
            fill=self.fill,
            fillable=self.fillable,
        )

    def __init__(
        self,
        _fn: Optional[ValueFn[ValueT]] = None,
        *,
        width: Optional[str] = None,
        height: Optional[str] = None,
        fill: Optional[bool] = None,
        fillable: Optional[bool] = None,
    ):
        super().__init__(_fn)
        self.width = width
        self.height = height
        self.fill = fill
        self.fillable = fillable

        self._value: ValueT | None = None
        self._widget: WidgetT | None = None
        self._contexts: set[Context] = set()

    async def render(self) -> Jsonifiable | None:
        with WidgetRenderContext():
            return await self._render()

    async def _render(self) -> Jsonifiable | None:
        session = get_current_session()
        lifecycle = None
        output_id = None
        if session is not None and not session.is_stub_session():
            lifecycle = get_lifecycle(session.root_scope())
            output_id = session.ns(self.output_id)

        try:
            value = await self.fn()
        except SilentCancelOutputException:
            # Keeping the previous output also keeps its publication/lease.
            raise
        except Exception:
            # An error replaces the output: the previous offer is invalidated.
            if lifecycle is not None and output_id is not None:
                lifecycle.retract(output_id)
            raise

        # Attach value/widget attributes to user func so they can be accessed (in other reactive contexts)
        self._value = value
        self._widget = None

        # Invalidate any reactive contexts that have read these attributes
        self._invalidate_contexts()

        if value is None:
            if lifecycle is not None and output_id is not None:
                lifecycle.retract(output_id)
            return None

        # Ensure we have a widget & smart layout defaults
        widget = as_widget(value)

        # Reject widgets that can't be displayed (closed, retired, or owned by
        # another session) before initialization/display.
        if lifecycle is not None:
            lifecycle.check_displayable(widget)

        widget, fill = set_layout_defaults(widget)

        self._widget = cast(WidgetT, widget)

        # Don't actually display anything unless this is a DOMWidget
        if not isinstance(widget, DOMWidget):
            if lifecycle is not None and output_id is not None:
                lifecycle.retract(output_id)
            return None

        if lifecycle is None or output_id is None:
            return {
                "model_id": str(widget.model_id),
                "fill": fill,
                "widget_pkg": widget_pkg(widget),
            }

        lifetime = WidgetRenderContext.get_render_lifetime()
        generation_id = lifetime.generation_id if lifetime is not None else ""
        model_id = str(widget.model_id)
        publication = lifecycle.publish(output_id, generation_id, model_id)

        return {
            "version": 1,
            "kind": "widget",
            "session_id": lifecycle.epoch.session_id,
            "model_namespace": lifecycle.epoch.model_namespace,
            "epoch_id": lifecycle.epoch.epoch_id,
            "output_id": output_id,
            "generation_id": generation_id,
            "offer_id": publication.offer_id,
            "candidate_lease_id": publication.provisional_lease_id,
            "model_id": model_id,
            "fill": fill,
            "widget_pkg": widget_pkg(widget),
        }

    @property
    def value(self) -> ValueT | None:
        return self._get_reactive_obj(self._value)

    @value.setter
    def value(self, value: object):
        raise RuntimeError(
            "The `value` attribute of a @render_widget function is read only."
        )

    @property
    def widget(self) -> WidgetT | None:
        return self._get_reactive_obj(self._widget)

    @widget.setter
    def widget(self, widget: object):
        raise RuntimeError(
            "The `widget` attribute of a @render_widget function is read only."
        )

    def _get_reactive_obj(self, x: T) -> T | None:
        self._register_current_context()
        if x is not None:
            return x
        if has_current_context():
            req(False)  # A widget/model hasn't rendered yet
        return None

    def _invalidate_contexts(self) -> None:
        for ctx in self._contexts:
            ctx.invalidate()

    # If the widget/value is read in a reactive context, then we'll need to invalidate
    # that context when the widget's value changes
    def _register_current_context(self) -> None:
        if not has_current_context():
            return
        self._contexts.add(get_current_context())


def has_current_context() -> bool:
    try:
        get_current_context()
        return True
    except RuntimeError:
        return False


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
        if layout.height is not None and layout.height != "auto":
            fill = False

    pkg = widget_pkg(widget)

    # Plotly provides it's own layout API (which isn't a subclass of ipywidgets.Layout)
    if pkg == "plotly":
        from plotly.basewidget import BaseFigureWidget
        from plotly.graph_objs import Layout as PlotlyLayout

        if isinstance(layout, PlotlyLayout):
            if layout.height is not None:
                fill = False
            # Default margins are also way too big
            layout.template.layout.margin = dict(  # pyright: ignore
                l=16, t=32, r=16, b=16
            )
            # Unfortunately, plotly doesn't want to respect the top margin template,
            # so change that 60px default to 32px
            if layout.margin["t"] == 60:  # pyright: ignore
                layout.margin["t"] = 32  # pyright: ignore
            # In plotly >=v6.0, the plot won't actually fill unless it's responsive
            if fill:
                widget._config = {"responsive": True, **widget._config}  # type: ignore

        if isinstance(widget, BaseFigureWidget):
            # Reassigning the layout to a FigureWidget drops installed callbacks;
            # use native update_layout instead.
            widget.update_layout(layout)
        else:
            widget.layout = layout

    # altair, confusingly, isn't setup to fill it's Layout() container by default. I
    # can't imagine a situation where you'd actually want it to _not_ fill the parent
    # container since it'll be contained within the Layout() container, which has a
    # full-fledged sizing API.
    if pkg == "altair":
        import altair as alt

        # Since as_widget() has already happened, we only need to handle JupyterChart
        if isinstance(widget, alt.JupyterChart):
            chart = cast(alt.JupyterChart, widget).chart  # type: ignore
            if isinstance(chart, alt.ConcatChart):
                # Throw warning to use ui.layout_column_wrap() instead
                warnings.warn(
                    "Consider using shiny.ui.layout_column_wrap() instead of alt.concat() "
                    "for multi-column layout (the latter doesn't support filling layout).",
                    stacklevel=2,
                )
            else:
                UndefinedType = alt.utils.schemapi.UndefinedType  # type: ignore
                if hasattr(chart, "width") and isinstance(chart.width, UndefinedType):  # type: ignore[reportMissingTypeStubs]
                    chart = chart.properties(width="container")  # type: ignore
                if hasattr(chart, "height") and isinstance(chart.height, UndefinedType):  # type: ignore[reportMissingTypeStubs]
                    chart = chart.properties(height="container")  # type: ignore
            widget.chart = chart

    return (widget, fill)


@dataclass
class _RenderingWidget:
    context: Context
    lifetime: Lifetime | None = None
    active: bool = True


# The render that is running in the current asyncio task. A ContextVar, because Shiny
# can run a session's outputs as concurrent tasks that interleave at each `await`, and
# each task needs to see only its own render.
_rendering_widget: ContextVar[_RenderingWidget | None] = ContextVar(
    "shinywidgets_rendering_widget", default=None
)


class WidgetRenderContext:
    """
    Record the widget render that is running in the current asyncio task.

    This is used to ensure that widget's that are initialized in a render_widget()
    context are cleaned up properly when that context is re-entered.

    The render Context is captured at __enter__ time so that init_shiny_widget can
    register cleanup callbacks on the correct Context, even if the widget is
    constructed inside a reactive.isolate() block (which temporarily replaces the
    current Context with a short-lived temporary one).
    """

    def __init__(self):
        self._rendering: _RenderingWidget | None = None
        self._token: Token[_RenderingWidget | None] | None = None

    def __enter__(self):
        context = get_current_context()
        lifetime: Lifetime | None = None
        session = get_current_session()
        if session is not None and not session.is_stub_session():
            lifecycle = get_lifecycle(session.root_scope())
            lifetime = lifecycle.new_render_lifetime()
            # Register retirement before any widget construction: Shiny invokes
            # late invalidation registration immediately, so a render whose
            # context is already invalidated never admits new temporary widgets.
            context.on_invalidate(lambda: lifecycle.retire_render(lifetime))
        self._rendering = _RenderingWidget(context, lifetime)
        self._token = _rendering_widget.set(self._rendering)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert self._rendering is not None and self._token is not None
        # A task started during the render has a copy of this render's value. Mark
        # it inactive, so a widget that such a task builds later is not tied to
        # this output.
        self._rendering.active = False
        _rendering_widget.reset(self._token)
        return False

    @staticmethod
    def _current() -> _RenderingWidget | None:
        rendering = _rendering_widget.get()
        if rendering is None or not rendering.active:
            return None
        return rendering

    @staticmethod
    def is_rendering_widget() -> bool:
        return WidgetRenderContext._current() is not None

    @staticmethod
    def get_render_lifetime() -> Lifetime | None:
        """
        The durable lifetime of the render running in the current asyncio task,
        if any. Unlike the lexical context manager, this lifetime survives the
        render block (it is retired when the render's Context invalidates).
        """
        rendering = WidgetRenderContext._current()
        if rendering is None:
            return None
        return rendering.lifetime

    @staticmethod
    def get_render_context() -> Context:
        """
        Get the reactive Context that was active when the render function started.

        This returns the render output's Context rather than the current Context,
        which may be a temporary isolate Context.
        """
        rendering = WidgetRenderContext._current()
        if rendering is None:
            raise RuntimeError("Not currently rendering a widget")
        return rendering.context
