from __future__ import annotations

import warnings
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    Iterator,
    Optional,
    Tuple,
    TypeVar,
    cast,
)
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

if TYPE_CHECKING:
    from ipysigma import Sigma

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
    # each handler may mutate the widget and/or revise `fill`
    for cls in type(widget).__mro__:
        defaults = _LAYOUT_DEFAULTS.get(widget_pkg(cls))
        if defaults is not None:
            fill = defaults(widget, fill)
            break

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


JSCATTER_DEFAULT_HEIGHT = 240
"""
The pixel height jscatter gives a `Scatter` unless the user sets one
"""

FILLING_JSCATTERS: WeakSet[DOMWidget] = WeakSet()
"""
jscatter widgets that were displayed with fill (see jscatter_layout_defaults())
"""


def jscatter_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # jupyter-scatter always has a pixel height (there's no "auto"), so the only
    # sign that the user chose one is a value other than jscatter's own default.
    # In a filling layout, the browser drives the height from the container size
    # (see jscatter in js/src/fill.ts) and syncs it to the widget, so a widget
    # that filled once (e.g., displayed again via session_lifetime()) must keep
    # filling rather than look like it has a user-chosen height.
    if widget in FILLING_JSCATTERS:
        return fill
    if getattr(widget, "height", JSCATTER_DEFAULT_HEIGHT) != JSCATTER_DEFAULT_HEIGHT:
        return False
    if fill:
        FILLING_JSCATTERS.add(widget)
    return fill


def _altair_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # altair, confusingly, isn't setup to fill it's Layout() container by default. I
    # can't imagine a situation where you'd actually want it to _not_ fill the parent
    # container since it'll be contained within the Layout() container, which has a
    # full-fledged sizing API.
    import altair as alt

    # Since as_widget() has already happened, we only need to handle JupyterChart
    if isinstance(widget, alt.JupyterChart):
        jchart = cast(alt.JupyterChart, widget)
        chart = cast("alt.typing.ChartType | None", jchart.chart)
        if isinstance(chart, alt.ConcatChart):
            # Throw warning to use ui.layout_column_wrap() instead
            warnings.warn(
                "Consider using shiny.ui.layout_column_wrap() instead of alt.concat() "
                "for multi-column layout (the latter doesn't support filling layout).",
                stacklevel=2,
            )
        else:
            UndefinedType = alt.utils.schemapi.UndefinedType  # type: ignore
            sizing: dict[str, str] = {}
            if hasattr(chart, "width") and isinstance(chart.width, UndefinedType):  # type: ignore[reportMissingTypeStubs]
                sizing["width"] = "container"
            if hasattr(chart, "height") and isinstance(chart.height, UndefinedType):  # type: ignore[reportMissingTypeStubs]
                sizing["height"] = "container"
            if sizing and chart is not None:
                # Reassigning `.chart` makes JupyterChart rebuild `.selections` and
                # `.params`, orphaning observers the user attached before returning
                # it, so patch the (vega-lite) spec instead. Check the spec itself
                # (not the active transformer): a chart assigned under the
                # vegafusion transformer has `.spec` set to None until the browser
                # reports its timezone, and a pre-transformed vega spec afterwards,
                # neither of which can be patched like this.
                spec = cast("dict[str, object] | None", jchart.spec)
                if isinstance(spec, dict) and "vega-lite" in str(spec.get("$schema")):
                    jchart.spec = {**spec, **sizing}
                else:
                    jchart.chart = chart.properties(**sizing)

    return fill


def ipysigma_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # Sigma always syncs a concrete CSS `height` (500px unless the user passes
    # `height`/`raw_height`), and its `layout` trait is a node-position dict rather
    # than an ipywidgets Layout, so the generic height check above can't see it.
    # Only the untouched default (including one set via `Sigma.set_defaults()`) is
    # treated as "unset".
    sigma = cast("Sigma", widget)
    if sigma.height == f"{type(sigma).default_height}px":
        sigma.height = "100%"
        return fill
    return fill and sigma.height == "100%"


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


def lonboard_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    from lonboard import Map  # pyright: ignore[reportMissingImports]

    if not isinstance(widget, Map):
        return fill

    # Map.__init__() sets layout.height to "100%" itself (deferring to the map's
    # own `height`), which the generic check above mistakes for a user-specified
    # height
    fill = widget.layout.height in (None, "auto", "100%")

    # The map's root element is styled `min-height: 100%; height: <height>`, so
    # with lonboard's default height it already grows to fill a definite-height
    # container (and shinywidgets.css clamps it so it can't overflow one). A
    # user-specified height, on the other hand, gets overridden by that
    # min-height, so size the widget container to the map rather than to its
    # parent.
    # pyright can't narrow via isinstance() when lonboard isn't installed
    # (e.g., Python 3.15)
    if widget.height not in (widget.trait_defaults("height"), "100%"):  # pyright: ignore[reportAttributeAccessIssue]
        fill = False
        if widget.layout.height == "100%":
            widget.layout.height = "auto"

    return fill


def ipyaladin_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    from ipyaladin import Aladin

    if not isinstance(widget, Aladin):
        return fill

    # The viewer's root is styled `height: <_height>px` (400 by default), which
    # shinywidgets.css sizes to the widget container instead, so a user-specified
    # height has to go on the container. The default can't be told apart from an
    # explicit 400, so treat it as unset (as maplibre_layout_defaults() does).
    # -1, ipyaladin's sentinel for "100% of the container", isn't an explicit
    # height either: filling is exactly what it asks for.
    height = _aladin_height_intent(widget)
    if height not in (400, -1):
        fill = False
        if widget.layout.height in (None, "auto"):
            widget.layout.height = f"{height}px"

    return fill


# Widget attribute recording the height the user asked an ipyaladin Aladin for
_ALADIN_HEIGHT_INTENT = "_shinywidgets_height_intent"


def _aladin_height_intent(widget: DOMWidget) -> int:
    # widget._height isn't a pure record of intent: the view also reports its
    # rendered height back on resize, so a filling widget kept alive across
    # renders (e.g., with session_lifetime()) picks up its container's height,
    # which a later render must not mistake for a user-specified height. Take
    # the first render's value as the intent, then revise it only on Python-side
    # changes (e.g., `widget.height = ...`).
    intent = getattr(widget, _ALADIN_HEIGHT_INTENT, None)
    if intent is not None:
        return cast(int, intent)

    intent = cast("int", widget._height)  # pyright: ignore[reportAttributeAccessIssue]
    setattr(widget, _ALADIN_HEIGHT_INTENT, intent)

    def _revise_intent(change: "dict[str, int]") -> None:
        # Front-end state updates go through Widget.set_state(), which keeps the
        # updated properties in _property_lock while notifications fire;
        # Python-side assignments don't. If ipywidgets ever drops _property_lock,
        # this degrades to treating resize feedback as intent (the behavior
        # before the intent was tracked separately).
        if not getattr(widget, "_property_lock", None):
            setattr(widget, _ALADIN_HEIGHT_INTENT, change["new"])

    widget.observe(_revise_intent, names="_height")
    return intent


def bokeh_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # Covers render_bokeh(), render_panel() and render_holoviews(): a bokeh root
    # that doesn't stretch vertically has a height of its own, so filling would
    # just reserve empty space below it. Panel propagates its sizing_mode (e.g.,
    # from HoloViews' responsive=True) to the root.
    from jupyter_bokeh import BokehModel

    if not isinstance(widget, BokehModel):
        return fill

    sizing_mode = getattr(widget._model, "sizing_mode", None)
    return fill and sizing_mode in (
        "stretch_both",
        "stretch_height",
        "scale_both",
        "scale_height",
    )


def maplibre_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    from maplibre.ipywidget import MapWidget

    if not isinstance(widget, MapWidget):
        return fill

    # The map's root element is styled `height: <height>` (shinywidgets.css
    # sizes it to the widget container instead), so a user-specified height has
    # to go on the container. The default (MapWidget.__init__()'s 400) can't be
    # told apart from an explicit 400, so treat it as unset, as with a
    # percentage (which is relative to the container anyway).
    if widget.height != "400px" and not str(widget.height).endswith("%"):
        fill = False
        if widget.layout.height in (None, "auto"):
            widget.layout.height = widget.height

    return fill


# Per-package layout adjustments for filling layouts, keyed by widget_pkg()
# (the same key used by AS_WIDGET_MAP in _as_widget.py and WIDGET_BEHAVIORS
# in js/src/fill.ts). A handler receives the widget and the current fill
# decision, applies package-specific mutations, and returns the (possibly
# revised) fill decision.
#
# N.B. a bokeh figure's default sizing_mode is set in as_widget_bokeh() instead
# (see the comment there for why it can't happen here).
_LAYOUT_DEFAULTS: dict[str, Callable[[DOMWidget, bool], bool]] = {
    "plotly": _plotly_layout_defaults,
    "altair": _altair_layout_defaults,
    "ipyaladin": ipyaladin_layout_defaults,
    "ipysigma": ipysigma_layout_defaults,
    "jscatter": jscatter_layout_defaults,
    "keplergl": keplergl_layout_defaults,
    "lonboard": lonboard_layout_defaults,
    "jupyter_bokeh": bokeh_layout_defaults,
    "maplibre": maplibre_layout_defaults,
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
