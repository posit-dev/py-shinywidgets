from __future__ import annotations

import warnings
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Callable, Generic, Iterator, Optional, Tuple, TypeVar, cast
from weakref import WeakSet

from htmltools import Tag
from ipywidgets.widgets import DOMWidget, Layout, Widget
from shiny import req
from shiny.reactive import Context
from shiny.reactive._core import (
    get_current_context,  # pyright: ignore[reportPrivateImportUsage]
)
from shiny.render.renderer import Jsonifiable, Renderer, ValueFn
from shiny.session import get_current_session

from ._as_widget import as_widget
from ._comm import OrphanedShinyComm
from ._dependencies import widget_pkg
from ._output_widget import output_widget
from ._widget_registry import WIDGET_INSTANCE_MAP

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
    """
    Base class for the render decorators in `shinywidgets._render_widget`.

    Handles coercion of the render function's return value into an ipywidget (via
    `_as_widget()`), applies smart layout defaults, and produces the payload that the
    browser-side output binding uses to display the widget.
    """

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
        value = await self.fn()

        # Attach value/widget attributes to user func so they can be accessed (in other reactive contexts)
        self._value = value
        self._widget = None

        # Invalidate any reactive contexts that have read these attributes
        self._invalidate_contexts()

        if value is None:
            return None

        # Ensure we have a widget & smart layout defaults
        widget = self._as_widget(value)
        if is_closed_widget(widget):
            raise RuntimeError(
                "This widget has been closed (its render was invalidated, or it was "
                "closed explicitly), so it can't be displayed again. To reuse a widget "
                "across renders, construct it inside `with session_lifetime():`."
            )

        session = get_current_session()
        # Outside a real session (the Express UI-discovery pass, or a unit test
        # that calls _render() directly without a session) there's nothing to
        # compare the returned widgets' ownership against, so there's nothing to
        # reject.
        if session is not None and not session.is_stub_session():
            # _shinywidgets imports WidgetRenderContext and is_closed_widget from
            # this module at module scope, so importing it back the same way would
            # be circular; keep this one function-local instead.
            from ._shinywidgets import foreign_or_closed_widget

            bad = foreign_or_closed_widget(widget, session.root_scope())
            if bad is not None and is_closed_widget(bad):
                raise RuntimeError(
                    f"{type(bad).__name__} was closed (its render was invalidated, or "
                    "it was closed explicitly), so it can't be displayed again. To "
                    "reuse a widget across renders, construct it inside "
                    "`with session_lifetime():`."
                )
            if bad is not None:
                raise RuntimeError(
                    f"{type(bad).__name__} belongs to another Shiny session, so it "
                    "can't be displayed here. Construct widgets per session."
                )

        widget, fill = set_layout_defaults(widget)

        self._widget = cast(WidgetT, widget)

        # Don't actually display anything unless this is a DOMWidget
        if not isinstance(widget, DOMWidget):
            return None

        return {
            "model_id": str(widget.model_id),
            "fill": fill,
            "widget_pkg": widget_pkg(widget),
        }

    def _as_widget(self, value: ValueT) -> WidgetT:
        """
        Coerce the user's return value into a Widget. Subclasses may override
        to support additional return shapes (e.g., a (value, options) tuple).
        """
        return cast(WidgetT, as_widget(value))

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

    # Package-specific adjustments (mirrors AS_WIDGET_MAP in _as_widget.py):
    # each handler may mutate the widget and/or tighten `fill` to False
    defaults = _LAYOUT_DEFAULTS.get(widget_pkg(widget))
    if defaults is not None:
        fill = defaults(widget, fill)

    return (widget, fill)


def _plotly_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # Plotly provides it's own layout API (which isn't a subclass of ipywidgets.Layout)
    from plotly.basewidget import BaseFigureWidget
    from plotly.graph_objs import Layout as PlotlyLayout

    layout = widget.layout  # type: ignore

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

    return fill


def _altair_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # altair, confusingly, isn't setup to fill it's Layout() container by default. I
    # can't imagine a situation where you'd actually want it to _not_ fill the parent
    # container since it'll be contained within the Layout() container, which has a
    # full-fledged sizing API.
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

    return fill


def keplergl_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # KeplerGl sizes itself from a pixel `height` trait (default 400), so the only
    # way to tell the user asked for a specific height is that it isn't the default.
    # The browser overwrites that trait with the size it measures, so decide once
    # per instance (the first time it's seen) to keep re-displays filling.
    from keplergl import KeplerGl

    default_height = KeplerGl.class_traits()["height"].default_value
    if widget in AUTO_SIZED_KEPLERGL_WIDGETS:
        return fill
    if isinstance(widget, KeplerGl) and widget.height != default_height:
        return False
    AUTO_SIZED_KEPLERGL_WIDGETS.add(widget)
    return fill


AUTO_SIZED_KEPLERGL_WIDGETS: WeakSet[Widget] = WeakSet()


# Per-package layout adjustments for filling layouts, keyed by widget_pkg()
# (the same key used by AS_WIDGET_MAP in _as_widget.py and WIDGET_BEHAVIORS
# in js/src/fill.ts). A handler receives the widget and the current fill
# decision, applies package-specific mutations, and returns the (possibly
# tightened) fill decision.
#
# N.B. bokeh is intentionally absent: its sizing_mode hack lives in
# as_widget_bokeh() because applying it here doesn't work (see the TODO
# there).
_LAYOUT_DEFAULTS: dict[str, Callable[[DOMWidget, bool], bool]] = {
    "plotly": _plotly_layout_defaults,
    "altair": _altair_layout_defaults,
    "keplergl": keplergl_layout_defaults,
}


# The render Context that is running in the current asyncio task, or None outside
# a render (or inside session_lifetime()). A ContextVar, because Shiny can run a
# session's outputs as concurrent tasks that interleave at each `await`, and each
# task needs to see only its own render.
#
# asyncio.create_task() snapshots the current contextvars, so a task started
# during a render keeps seeing that render's Context even after the render body
# has returned. A widget the task builds later still registers for cleanup on
# that Context (see RENDER_OWNED_WIDGETS in _shinywidgets.py), same as one built
# directly in the render body -- it closes with the render instead of leaking
# until the session ends.
_rendering_widget: ContextVar[Context | None] = ContextVar(
    "shinywidgets_rendering_widget", default=None
)


class WidgetRenderContext:
    """
    Record the reactive Context of the widget render running in the current
    asyncio task.

    This is used to ensure that widgets initialized in a render_widget() context
    are cleaned up properly when that context is invalidated.

    The render Context is captured at __enter__ time so that init_shiny_widget can
    register cleanup callbacks on the correct Context, even if the widget is
    constructed inside a reactive.isolate() block (which temporarily replaces the
    current Context with a short-lived temporary one).
    """

    def __init__(self):
        self._context: Context | None = None
        self._token: Token[Context | None] | None = None

    def __enter__(self):
        self._context = get_current_context()
        self._token = _rendering_widget.set(self._context)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert self._context is not None and self._token is not None
        _rendering_widget.reset(self._token)
        return False

    @staticmethod
    def is_rendering_widget() -> bool:
        return _rendering_widget.get() is not None

    @staticmethod
    @contextmanager
    def suspended() -> Iterator[None]:
        """Widgets constructed in the block get session (not render) lifetime."""
        token = _rendering_widget.set(None)
        try:
            yield
        finally:
            _rendering_widget.reset(token)

    @staticmethod
    @contextmanager
    def resumed(context: Context | None) -> Iterator[None]:
        """Re-enter a render captured earlier, so widgets created now share its cleanup."""
        token = _rendering_widget.set(context)
        try:
            yield
        finally:
            _rendering_widget.reset(token)

    @staticmethod
    def get_render_context() -> Context:
        """
        Get the reactive Context that was active when the render function started.

        This returns the render output's Context rather than the current Context,
        which may be a temporary isolate Context.
        """
        context = _rendering_widget.get()
        if context is None:
            raise RuntimeError("Not currently rendering a widget")
        return context


def is_closed_widget(widget: Widget) -> bool:
    """
    A widget we closed keeps an inert OrphanedShinyComm (so model_id still works)
    but is no longer in ipywidgets' instance map; a user-closed widget has no comm.
    """
    if widget.comm is None:
        return True
    return (
        isinstance(widget.comm, OrphanedShinyComm)
        and WIDGET_INSTANCE_MAP.get(widget.model_id) is not widget
    )
