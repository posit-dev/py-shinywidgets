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

from ._as_widget import as_widget, refresh_stale_mpl_canvases
from ._comm import OrphanedShinyComm
from ._dependencies import widget_pkg
from ._output_widget import output_widget
from ._widget_registry import WIDGET_INSTANCE_MAP

if TYPE_CHECKING:
    from ipysigma import Sigma
    from itables.widget import ITable

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

        session = get_current_session()
        # _shinywidgets imports WidgetRenderContext and is_closed_widget from
        # this module at module scope, so importing it back the same way would
        # be circular; keep this one function-local instead.
        from ._shinywidgets import (
            foreign_or_closed_widget,
            open_process_global_widgets,
            ownership_error,
        )

        # Outside a real session (the Express UI-discovery pass, or a unit test
        # that calls _render() directly without a session) there's nothing to
        # compare the returned widgets' ownership against, so only a closed
        # root can be rejected.
        if session is None or session.is_stub_session():
            if is_closed_widget(widget):
                raise ownership_error(widget)
        else:
            root = session.root_scope()
            bad = foreign_or_closed_widget(widget, root)
            if bad is not None:
                raise ownership_error(bad)
            # Only once nothing raised, so a rejected render opens nothing
            open_process_global_widgets(widget, root)

        # A canvas nested in the returned widget may have been coerced (and
        # drawn) earlier and then had its figure changed; refresh its initial
        # image here, where a draw error is still this output's error. After
        # the ownership check, since drawing updates browser-synced state.
        refresh_stale_mpl_canvases(widget)

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

    # Do nothing for "input-like" widgets (e.g., ipywidgets.IntSlider()),
    # unless a package-specific handler below applies (e.g., trame_pyvista's
    # html-backend widget is an ipywidgets HTML output, not an input)
    if getattr(
        widget, "_model_module", None
    ) == "@jupyter-widgets/controls" and not any(
        widget_pkg(cls) in _LAYOUT_DEFAULTS for cls in type(widget).__mro__
    ):
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


K3D_DEFAULT_HEIGHT = 512


def k3d_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    from k3d.plot import Plot

    # k3d.plot() always sets `height` explicitly (in pixels, default 512), so the
    # default value is the only signal that the user didn't ask for a height. When
    # filling, the plot's pixel height is only a flex basis (the `.lm-Widget`
    # container stretches it), so no adjustment is needed.
    if isinstance(widget, Plot) and widget.height != K3D_DEFAULT_HEIGHT:
        return False
    return fill


def pygwalker_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # PyGWalker's UI is ~750px tall regardless of its container, so rather than
    # being clipped by a shorter container (or explicit height), let it scroll.
    # Sizing to 100% of the container is what makes an output_widget(height=...)
    # (which, unlike fill, doesn't constrain the child) apply to the widget.
    layout = widget.layout  # type: ignore
    if layout.overflow is None:
        layout.overflow = "auto"
    if layout.height in (None, "auto"):
        layout.height = "100%"
    # This runs on every render, so a widget that's rendered again (e.g., one
    # reused via session_lifetime()) already has the "100%" written above, which
    # set_layout_defaults() reads as an explicit height.
    return fill or layout.height == "100%"


def ipyvolume_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    from ipyvolume.widgets import Figure

    if not isinstance(widget, Figure):
        return fill

    # A figure's width/height are its WebGL canvas size in pixels. Treat both
    # "default" sizes as unset: the trait default (500x400) and the one
    # ipv.figure()/quickscatter() always passes explicitly (400x500). When
    # filling, the browser resizes the canvas to the container (see
    # WIDGET_BEHAVIORS in js/src/fill.ts) and saves the measured size back to
    # these traits, so also treat a size matching the last browser sync as
    # unset -- otherwise re-rendering a cached, session-lifetime figure would
    # mistake the browser's measurements for an explicit user size (while a
    # size the user assigned after that sync still counts as explicit).
    size = (widget.width, widget.height)
    # Called unconditionally (even for a default-sized figure, where the
    # answer is already known): it installs the sync tracking that later
    # renders of this same figure rely on
    synced = _frontend_size(widget)
    if size in ((500, 400), (400, 500)) or size == synced:
        return fill
    return False


# Widget attribute names used by _frontend_size() to track the figure size
# last synced from the browser (see below)
_FRONTEND_SIZE_ATTR = "_shinywidgets_frontend_size"
_FRONTEND_SIZE_TRACKING_ATTR = "_shinywidgets_tracking_frontend_size"


def _frontend_size(widget: Widget) -> Optional[Tuple[int, int]]:
    """
    The (width, height) last synced from the browser, or None.

    Installs (once) a wrapper on the widget's set_state() -- the method
    front-end "update" messages go through -- that records width/height
    syncs, so the browser resizer's measurements can be told apart from
    sizes the user assigned in Python.
    """
    if not getattr(widget, _FRONTEND_SIZE_TRACKING_ATTR, False):
        original = widget.set_state

        def set_state(sync_data: dict) -> None:  # pyright: ignore[reportMissingParameterType]
            if "width" in sync_data or "height" in sync_data:
                # sync_data may update only one of the two traits; the other
                # keeps its current value (set_state applies the state after
                # this wrapper runs). Only called with widgets that have
                # width/height traits (e.g., ipyvolume.Figure).
                setattr(
                    widget,
                    _FRONTEND_SIZE_ATTR,
                    (
                        sync_data.get("width", getattr(widget, "width")),
                        sync_data.get("height", getattr(widget, "height")),
                    ),
                )
            original(sync_data)

        setattr(widget, "set_state", set_state)
        setattr(widget, _FRONTEND_SIZE_TRACKING_ATTR, True)

    return getattr(widget, _FRONTEND_SIZE_ATTR, None)


def itables_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # DataTables only gets a scrollable body (which is what lets the table fill
    # its container instead of growing past it) when scrollY is set, so default it
    # unless the user chose their own. shinywidgets.css does the actual filling for
    # widgets with the marker class.
    from itables import options as itables_options

    # ITable has no public API for these traits, so the private attributes are used
    table = cast("ITable", widget)
    dt_args = table._dt_args
    if "scrollY" in dt_args:
        return fill

    table._dt_args = {**dt_args, "scrollY": "100%"}
    table.add_class("shinywidgets-itables-fill")

    # An in-place `update(scrollY=...)` after rendering supersedes the scrollY
    # defaulted above, so drop the marker class whose CSS forces the scroll body
    # to fill its container (it would override the requested height). Anything
    # but the defaulted "100%" counts as a user choice.
    def sync_fill_marker(change: dict[str, object]) -> None:
        new_args = cast("dict[str, object]", change["new"])
        if new_args.get("scrollY") != "100%":
            table.remove_class("shinywidgets-itables-fill")
            table.unobserve(sync_fill_marker, "_dt_args")

    table.observe(sync_fill_marker, "_dt_args")

    # itables' default `width:auto` leaves a scrolling table's header and body
    # columns misaligned (a style the user chose is left alone). With scrollX,
    # itables rewrites the default margin:auto to margin:0 before we see it, so
    # normalize the default before comparing.
    # (itables_types declares options.style as a dict, but at runtime it is a str)
    default_style = cast("str", itables_options.style)
    if dt_args.get("scrollX"):
        default_style = default_style.replace("margin:auto", "margin:0")
    if table._style == default_style:
        table._style = table._style.replace("width:auto", "width:100%")
    return fill


def geolibre_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    from geolibre import Map

    if not isinstance(widget, Map):
        return fill

    # The embedded app reads the `height` trait once, when it loads (styling
    # its <iframe>), so changing it after rendering has no effect. The
    # default ("800px") can't be told apart from an explicit one, so treat it
    # as unset (as ipyaladin_layout_defaults() does): in a filling layout,
    # size the iframe to its container; any other height opts out of filling
    # (the front-end applies it to the iframe directly).
    if widget.height != "800px":
        return False
    if fill:
        widget.height = "100%"
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


def ipycanvas_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # A canvas has fixed pixel dimensions (its width/height traits), which
    # aren't layout sizes: stretching the element to fill would scale the
    # bitmap (blurry). Keep the fill decision (so the output claims the
    # container) and instead mark the widget so shinywidgets.css centers it
    # (shrinking to fit, aspect preserved) within the filled container.
    widget.add_class("shinywidgets-ipycanvas")
    return fill


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


# leafmap's widget backends all default to a 600px height, in whichever way the
# backend sizes itself: `Layout.height` for the ipyleaflet backend, a `height`
# trait for maplibre, `layout.height` for plotly.
_LEAFMAP_DEFAULT_HEIGHT = 600


def leafmap_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # That 600px is leafmap's default rather than user intent, so treat it as
    # unset and let the map fill its container like other map widgets do. (As
    # with maplibre's own 400px default, a user-specified 600 can't be told
    # apart from it.) Anything else is a height the user asked for, which the
    # backend's own handler deals with.
    from ipyleaflet import Map as LeafletMap

    if isinstance(widget, LeafletMap):
        if widget.layout.height != f"{_LEAFMAP_DEFAULT_HEIGHT}px":
            return fill
        # Fill via CSS, as if the map hadn't set a height at all
        # (shinywidgets.css lays a leaflet map out as a flex column sized to
        # its output)
        widget.layout.height = "100%"
        return True

    from maplibre.ipywidget import MapWidget

    if isinstance(widget, MapWidget):
        if widget.height != f"{_LEAFMAP_DEFAULT_HEIGHT}px":
            return maplibre_layout_defaults(widget, fill)
        # maplibre sizes its root element from its own `height` trait, which
        # shinywidgets.css in turn sizes to the widget container
        widget.height = "100%"
        return True

    from plotly.basewidget import BaseFigureWidget

    if isinstance(widget, BaseFigureWidget):
        if getattr(widget.layout, "height", None) == _LEAFMAP_DEFAULT_HEIGHT:
            widget.layout.height = None  # pyright: ignore[reportAttributeAccessIssue]
        return _plotly_layout_defaults(widget, fill)

    # Anything else (e.g., the kepler.gl backend, whose 600 is leafmap's default
    # but which already fills its container) keeps the generic decision
    return fill


PYTHREEJS_DEFAULT_SIZE = 200

# Attributes stashed on a pythreejs Renderer by _track_pythreejs_sizing_intent()
_PYTHREEJS_FILL_INTENT = "_shinywidgets_pythreejs_fill"
_PYTHREEJS_FRONTEND_UPDATE = "_shinywidgets_pythreejs_frontend_update"


def pythreejs_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    from pythreejs import Renderer

    if not isinstance(widget, Renderer):
        return fill

    intent = cast(Optional[bool], getattr(widget, _PYTHREEJS_FILL_INTENT, None))
    if intent is None:
        # A pythreejs Renderer draws into a fixed pixel-size canvas, so an
        # explicit width/height is a request for that size rather than
        # filling. The 200x200 default can't be told apart from an explicit
        # 200x200 (Renderer.__init__() sets it either way), so the default is
        # treated as unset.
        intent = (
            widget.width == PYTHREEJS_DEFAULT_SIZE
            and widget.height == PYTHREEJS_DEFAULT_SIZE
        )
        _track_pythreejs_sizing_intent(widget, intent)
    return fill and intent


def _track_pythreejs_sizing_intent(renderer: DOMWidget, intent: bool) -> None:
    # setupPythreejsResize() (js/src/fill.ts) syncs a filling Renderer's pixel
    # size back to Python, so the live width/height of a reused Renderer
    # (e.g., one cached with session_lifetime() and returned on a later
    # render) reflect its container, not the user's intent. Record the
    # first-render decision and revisit it only on size changes that didn't
    # come from the front-end (front-end state updates all arrive through
    # Widget.set_state()), so an explicit user size change is still honored.
    setattr(renderer, _PYTHREEJS_FILL_INTENT, intent)
    setattr(renderer, _PYTHREEJS_FRONTEND_UPDATE, False)

    set_state = renderer.set_state

    def set_state_tracking_frontend(sync_data: dict[str, Jsonifiable]) -> None:
        setattr(renderer, _PYTHREEJS_FRONTEND_UPDATE, True)
        try:
            set_state(sync_data)
        finally:
            setattr(renderer, _PYTHREEJS_FRONTEND_UPDATE, False)

    renderer.set_state = set_state_tracking_frontend  # type: ignore[method-assign]

    def update_intent(change: object) -> None:
        if getattr(renderer, _PYTHREEJS_FRONTEND_UPDATE):
            return
        setattr(
            renderer,
            _PYTHREEJS_FILL_INTENT,
            renderer.width == PYTHREEJS_DEFAULT_SIZE  # type: ignore[attr-defined]
            and renderer.height == PYTHREEJS_DEFAULT_SIZE,  # type: ignore[attr-defined]
        )

    renderer.observe(update_intent, names=["width", "height"])


def pyvista_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    from trame_pyvista.jupyter import EmbeddableWidget  # pyright: ignore[reportMissingImports]

    if not isinstance(widget, EmbeddableWidget):
        return fill

    # as_widget_pyvista() sets layout height to "100%" (sizing the iframe to
    # the container), which the generic check above mistakes for a
    # user-specified height. A height the user set themselves is still
    # respected (they don't get fill).
    return widget.layout.height in (None, "auto", "100%")


def vizarr_layout_defaults(widget: DOMWidget, fill: bool) -> bool:
    # vizarr's Viewer styles its root element with an inline `height` taken from
    # its `height` trait (default "500px"), which the generic Layout check above
    # can't see (the layout is an ordinary ipywidgets Layout). Only the
    # untouched default counts as unset. The marker class lets shinywidgets.css
    # fit the viewer to an output with an explicit height (which, unlike a
    # filling layout, doesn't stretch the viewer on its own).
    widget.add_class("shinywidgets-vizarr")
    height = getattr(widget, "height", None)
    if height is not None and height != widget.trait_defaults("height"):
        return False
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
    "geolibre": geolibre_layout_defaults,
    "ipyvolume": ipyvolume_layout_defaults,
    "ipyaladin": ipyaladin_layout_defaults,
    "ipycanvas": ipycanvas_layout_defaults,
    "ipysigma": ipysigma_layout_defaults,
    "itables": itables_layout_defaults,
    "jscatter": jscatter_layout_defaults,
    "pygwalker": pygwalker_layout_defaults,
    "k3d": k3d_layout_defaults,
    "keplergl": keplergl_layout_defaults,
    "lonboard": lonboard_layout_defaults,
    "jupyter_bokeh": bokeh_layout_defaults,
    "leafmap": leafmap_layout_defaults,
    "maplibre": maplibre_layout_defaults,
    "pythreejs": pythreejs_layout_defaults,
    # pyvista's html jupyter backend widget lives in the trame_pyvista package
    "trame_pyvista": pyvista_layout_defaults,
    "vizarr": vizarr_layout_defaults,
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
