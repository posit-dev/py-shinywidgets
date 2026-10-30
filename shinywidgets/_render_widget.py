from __future__ import annotations

import sys
import warnings
from importlib.metadata import version as package_version
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from htmltools import Tag
from ipywidgets.widgets.widget import Widget
from packaging.version import Version

if TYPE_CHECKING:
    # Absent from 3.15+ environments (duckdb has no cp315 wheels, so its
    # dependents are excluded there; see pyproject.toml)
    import duckdb  # pyright: ignore[reportMissingImports]
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from altair import JupyterChart
    from bokeh.events import RangesUpdate, Tap
    from bqplot import Figure as BqplotFigure
    from drawdata import BarWidget as DrawdataBarWidget
    from drawdata import ScatterWidget as DrawdataScatterWidget
    from geolibre import Map as GeolibreMap
    from ipyaladin import Aladin
    from ipycanvas import Canvas as IpycanvasCanvas
    from ipycanvas import MultiCanvas, MultiRoughCanvas, RoughCanvas
    from ipycytoscape import CytoscapeWidget
    from ipydatagrid import DataGrid
    from ipyfilechooser import FileChooser
    from ipyleaflet import Map as LeafletMap
    from ipympl.backend_nbagg import Canvas as MplCanvas
    from ipyniivue import NiiVue
    from ipysigma import Sigma
    from ipyvolume.widgets import Figure as IpyvolumeFigure

    # pygwalker 0.6 renamed its widget class (_WalkerWidget ->
    # pygwalker.services.anywidget_widget.WalkerAnyWidget), so type both by
    # their common public base
    from ipywidgets import Widget as WalkerWidget
    from itables.widget import ITable
    from jscatter.widget import JupyterScatter
    from jupyter_bokeh import BokehModel
    from k3d.plot import Plot as K3dPlot
    from keplergl import KeplerGl
    from lonboard import Map as LonboardMap  # pyright: ignore[reportMissingImports]
    from maplibre.ipywidget import MapWidget
    from maplibre.map import Map as MaplibreMap
    from mosaic_widget import MosaicWidget  # pyright: ignore[reportMissingImports]
    from narwhals.typing import IntoDataFrameT
    from nglview import NGLWidget
    from perspective.widget import PerspectiveWidget
    from plotly.graph_objects import FigureWidget
    from pydeck.widget import DeckGLWidget
    from pyobsplot.widget import ObsplotWidget

    from ._altair import Selection

    # embedding-atlas requires Python 3.11+, so it's absent from 3.10 environments
    if sys.version_info >= (3, 11):
        from embedding_atlas.widget import EmbeddingAtlasWidget  # pyright: ignore[reportMissingImports]
    else:
        from ipywidgets import Widget as EmbeddingAtlasWidget
    from pythreejs import Renderer as PythreejsRenderer
    from pyvista import Plotter as PyvistaPlotter  # pyright: ignore[reportMissingImports]
    from quak import Widget as QuakWidget  # pyright: ignore[reportMissingImports]
    from trame_pyvista.jupyter import EmbeddableWidget as PyvistaHtmlWidget  # pyright: ignore[reportMissingImports]

    # rerun requires Python 3.11+, so it's absent from 3.10 environments
    if sys.version_info >= (3, 11):
        from rerun.notebook import Viewer as RerunViewer
        from rerun_notebook import Viewer as RerunNotebookViewer
    else:
        from ipywidgets import Widget as RerunNotebookViewer
        from ipywidgets import Widget as RerunViewer

    # vizarr isn't in the dev/test groups (it pins zarr<3)
    from vizarr import Viewer as VizarrViewer  # pyright: ignore[reportMissingImports]
else:
    JupyterChart = DataGrid = ITable = JupyterScatter = KeplerGl = MplCanvas = Sigma = (
        BokehModel
    ) = MapWidget = FigureWidget = DeckGLWidget = MosaicWidget = BqplotFigure = (
        CytoscapeWidget
    ) = base = EmbeddingAtlasWidget = K3dPlot = LeafletMap = WalkerWidget = (
        FileChooser
    ) = NGLWidget = object
    Aladin = IpycanvasCanvas = MultiCanvas = MultiRoughCanvas = RoughCanvas = (
        LonboardMap
    ) = QuakWidget = PerspectiveWidget = GeolibreMap = IpyvolumeFigure = (
        PythreejsRenderer
    ) = PyvistaPlotter = PyvistaHtmlWidget = ObsplotWidget = VizarrViewer = (
        RerunViewer
    ) = RerunNotebookViewer = NiiVue = object

from shiny.render.renderer import ValueFn

from ._accessors import RatePolicy
from ._altair import ALTAIR_ACCESSORS, chart_frame, filter_selection, pick_selection
from ._as_widget import (
    PYDECK_NO_WIDGET_MESSAGE,
    as_widget_panel,
    networkx_to_sigma,
    perspective_widget,
    pydeck_has_widget,
)
from ._bokeh import _bokeh_dependency
from ._bokeh_accessors import BOKEH_ACCESSORS, selected_frame
from ._dependencies import widget_pkg
from ._itables import ITABLES_ACCESSORS
from ._jscatter import JSCATTER_ACCESSORS
from ._plotly import PLOTLY_ACCESSORS, Point, select_rows
from ._render_widget_base import ValueT, WidgetT, render_widget_base

if TYPE_CHECKING:
    # The values a @render_plotly render function may return (bound below):
    # a plotly figure (raw or pre-built FigureWidget -- sibling classes, so
    # both are listed), optionally paired with a Plotly.js config dict.
    PlotlyFigure = Union[go.Figure, go.FigureWidget]
    PlotlyValue = Union[PlotlyFigure, Tuple[PlotlyFigure, Dict[str, Any]]]

# The bound is a string so it stays a lazy forward reference at runtime (the
# alias it points to references plotly, an optional dependency).
PlotlyValueT = TypeVar("PlotlyValueT", bound="PlotlyValue")
# MapWidget subclasses maplibre.Map, so this bound covers both.
MaplibreValueT = TypeVar("MaplibreValueT", bound="MaplibreMap")
# String bound for the same reason as PlotlyValueT (ipycanvas is optional).
# The canvas classes are all widgets and there's no coercion, so this bounds
# both the render function's value and the rendered widget.
IpycanvasCanvasT = TypeVar(
    "IpycanvasCanvasT",
    bound="Union[IpycanvasCanvas, MultiCanvas, RoughCanvas, MultiRoughCanvas]",
)
# String bound for the same reason as PlotlyValueT (drawdata is optional).
# Both drawdata widgets are returned as-is (no coercion), so this bounds both
# the render function's value and the rendered widget.
DrawdataWidgetT = TypeVar(
    "DrawdataWidgetT",
    bound="Union[DrawdataScatterWidget, DrawdataBarWidget]",
)
# The values a @render_rerun render function may return: rerun's high-level
# notebook Viewer (coerced to its inner widget) or the rerun_notebook widget
# itself. String bound since rerun is an optional dependency.
RerunValueT = TypeVar("RerunValueT", bound="Union[RerunViewer, RerunNotebookViewer]")

if TYPE_CHECKING:
    # The values a @render_pyvista render function may return (bound below):
    # a pyvista Plotter or the pre-exported html-backend widget itself.
    PyvistaValue = Union[PyvistaPlotter, PyvistaHtmlWidget]
PyvistaValueT = TypeVar("PyvistaValueT", bound="PyvistaValue")

__all__ = (
    "render_widget",
    "render_altair",
    "render_bokeh",
    "render_embedding_atlas",
    "render_bqplot",
    "render_drawdata",
    "render_geolibre",
    "render_holoviews",
    "render_ipyaladin",
    "render_ipycanvas",
    "render_ipycytoscape",
    "render_ipydatagrid",
    "render_ipyfilechooser",
    "render_ipyleaflet",
    "render_ipysigma",
    "render_ipyvolume",
    "render_itables",
    "render_jscatter",
    "render_k3d",
    "render_keplergl",
    "render_leafmap",
    "render_lonboard",
    "render_maplibre",
    "render_matplotlib",
    "render_mosaic_widget",
    "render_nglview",
    "render_niivue",
    "render_obsplot",
    "render_panel",
    "render_perspective",
    "render_plotly",
    "render_plotnine",
    "render_pydeck",
    "render_pygwalker",
    "render_pythreejs",
    "render_pyvista",
    "render_quak",
    "render_vizarr",
    "render_rerun",
)


# In the generic case, just relay whatever the user's return type is
# since we're not doing any coercion
class render_widget(render_widget_base[WidgetT, WidgetT]):
    """
    Reactively render an ipywidget as a Shiny output.

    The decorated function should return an `ipywidgets.Widget`. (Other return values
    are passed through `as_widget()`, which coerces objects from several popular
    packages, but prefer the dedicated decorators like `render_plotly` for those, since
    they provide better type checking.)

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `ipywidgets.Widget` instance. Use `.widget` to programmatically update the
    rendered widget in place (trait changes on the widget are synced to the browser),
    or to reactively read widget state with :func:`~shinywidgets.reactive_read`.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    rate_policy
        How to rate-limit accessors on this renderer that declare a default
        policy, and :func:`~shinywidgets.reactive_read` on its widget. ``None``
        (the default) leaves each accessor's own default in place, and
        debounces ``reactive_read()`` only if ``rate_delay`` is given.
    rate_delay
        The rate-limit window in seconds. ``0`` disables rate limiting.
        Defaults to each accessor's own setting (0.25 for those that declare
        one).

    Examples
    --------
    ```python
    from shiny import App, ui
    from shinywidgets import output_widget, render_widget
    import ipywidgets as widgets

    app_ui = ui.page_fluid(output_widget("slider"))


    def server(input, output, session):
        @render_widget
        def slider():
            return widgets.IntSlider(value=5, min=0, max=10)


    app = App(app_ui, server)
    ```
    """


class render_drawdata(render_widget_base[DrawdataWidgetT, DrawdataWidgetT]):
    """
    Reactively render a [drawdata](https://github.com/koaning/drawdata) drawing
    widget as a Shiny output.

    The decorated function should return a `drawdata.ScatterWidget` or
    `drawdata.BarWidget` (requires ``pip install 'shinywidgets[drawdata]'``).
    The widget fills the output's width while preserving its aspect ratio
    (upstream, both widgets cap their display at their ``width``/``height``
    traits; shinywidgets lifts that cap so they scale like other outputs).
    The constructor's ``width``/``height`` define the drawing's *data
    coordinate space* -- drawn points are stored in those coordinates, with
    ``y`` pointing up -- and the aspect ratio, not the display size, so
    choose them for the coordinate range and shape you want, not for pixels.

    The decorated function also gains two read-only attributes: `.value` and
    `.widget`, both the rendered widget. Use `.widget` to programmatically
    update the widget in place, or to reactively read widget state (e.g., the
    drawn points via ``"data"``) with :func:`~shinywidgets.reactive_read`.

    Note
    ---
    **Drawn data syncs one batch behind** (upstream drawdata issue
    [#40](https://github.com/koaning/drawdata/issues/40), any frontend):
    `ScatterWidget`'s frontend mutates the model's ``data`` array in place, so
    the change from the *first* drawing batch goes undetected and nothing
    syncs until a second batch is drawn (from then on, every batch syncs in
    full). The undo (pops one batch) and reset buttons sync immediately.
    `BarWidget` is not affected.

    Also note a few `BarWidget` limitations (upstream drawdata issue
    [#42](https://github.com/koaning/drawdata/issues/42)): its frontend
    overwrites any ``data`` passed to the constructor when it initializes
    (all bins start at ``y_min``), so a `BarWidget` output always starts
    empty -- seeding initial data is impossible, even via a re-render --
    and it ignores later Python-side trait updates until the next re-render
    (it registers no ``change:`` handlers, unlike `ScatterWidget`).
    Re-rendering (returning a new `BarWidget` in response to a reactive
    change) is the way to change ``n_bins``, ``y_max``, etc. Finally, avoid
    putting two `BarWidget`s on the same page: clicking one widget's
    collection buttons silently switches the other's active collection
    (upstream drawdata issue
    [#43](https://github.com/koaning/drawdata/issues/43)).

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default),
        the height follows from the filled width and the widget's aspect ratio.
    fill
        Whether the output should grow or shrink to fit its parent container.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Examples
    --------
    ```python
    from drawdata import ScatterWidget
    from shiny import App, render, ui
    from shinywidgets import output_widget, reactive_read, render_drawdata

    app_ui = ui.page_fluid(
        output_widget("canvas"),
        ui.output_text_verbatim("n_points"),
    )


    def server(input, output, session):
        @render_drawdata
        def canvas():
            return ScatterWidget()

        @render.text
        def n_points():
            return len(reactive_read(canvas.widget, "data"))


    app = App(app_ui, server)
    ```
    """


# Package specific renderers that require coercion (via as_widget())
# NOTE: the types on these classes should mirror what as_widget() does
class render_altair(render_widget_base[ValueT, JupyterChart]):
    """
    Reactively render an [altair](https://altair-viz.github.io) chart as a Shiny output.

    The decorated function may return either an `altair.Chart` (which is coerced to
    an `altair.JupyterChart` widget) or an `altair.JupyterChart` widget (requires
    ``pip install 'shinywidgets[altair]'``).

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `JupyterChart` instance. Use `.widget` to programmatically update the rendered
    chart in place (trait changes on the widget are synced to the browser), or to
    reactively read widget state with :func:`~shinywidgets.reactive_read`.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Note
    ---
    **Reacting to selections**: give each selection a name (e.g.,
    ``alt.selection_interval(name="brush")``; altair's generated names change
    between renders). Then read it in a reactive function (a ``@render.*``
    function, ``@reactive.calc``, or ``@reactive.effect``), which re-runs
    whenever the user changes it, much like ``input.my_slider()``:

    * ``chart.selected("brush")``: the selection's current state.
    * ``chart.selected_rows("brush")``: the rows of the chart's data it selects,
      evaluated the way Vega-Lite does (including binned and date fields).

    How they behave:

    * Unlike other renderers' accessors, ``selected()`` isn't ``None`` once the
      chart has rendered: altair reports its selections from the start, so it's
      an empty selection (and ``selected_rows()`` an empty frame) until the user
      selects.
    * A re-render (e.g. when the render function reads an input) gives the user
      a new chart, whose selections start out empty.
    * While the user drags, they update at most once the user pauses for 250 ms
      (see ``rate_policy`` and ``rate_delay``).
    * They can't be read inside this output's own render function, which builds
      a new chart each time it runs. To change the chart in response, set a
      param (below) from a ``@reactive.effect``.

    **Params**: selections can't be set from Python, but params can: setting
    ``chart.widget.params.<name> = value`` updates the chart in place without
    re-sending its data. Prefer params
    (or a re-render) over replacing ``chart.widget.chart``, which re-sends the data,
    drops the container sizing described below, and replaces
    ``chart.widget.selections`` and ``chart.widget.params``.

    **Sizing**: a chart without an explicit width or height is sized to fill its
    output (``"container"``). Concatenated, faceted, and repeated charts keep their
    natural size.

    **Offline use**: `JupyterChart` loads its JavaScript from a CDN; call
    ``alt.JupyterChart.enable_offline()`` (requires ``vl-convert-python``) for apps
    that run without internet access.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    rate_policy
        How to rate-limit :meth:`selected` (debounced by default) and
        :func:`~shinywidgets.reactive_read` on the widget: ``"debounce"`` or
        ``"throttle"``. ``None`` (the default) keeps the debounce, and
        debounces ``reactive_read()`` only if ``rate_delay`` is given.
    rate_delay
        The rate-limit window in seconds (default 0.25). ``0`` disables rate
        limiting.
    """

    _accessor_specs = ALTAIR_ACCESSORS

    def selected(self, name: Optional[str] = None) -> Selection:
        """
        The current state of one of the chart's selections: an altair
        `IntervalSelection`, `PointSelection`, or `IndexSelection` (see
        `altair.utils.selection`), whose ``.value`` holds what's selected.

        Unlike other renderers' accessors, this is never ``None`` once the
        chart has rendered: until the user selects, it's an empty selection.
        `name` is the name given to the selection (e.g.
        ``alt.selection_interval(name="brush")``), and may be omitted when the
        chart has only one. Always name selections: altair's generated names
        change between renders. Debounced (250 ms) by default; see the
        ``rate_policy`` and ``rate_delay`` parameters.
        """
        selections = cast(Dict[str, "Selection"], self._read_accessor("selected"))
        return pick_selection(selections, name)

    def selected_rows(
        self, name: Optional[str] = None, *, df: Optional[IntoDataFrameT] = None
    ) -> IntoDataFrameT:
        """
        The rows of `df` in a selection (see :meth:`selected`), evaluated the
        way Vega-Lite does (including binned and temporal fields).

        `df` defaults to the chart's own data frame (pandas or polars); pass it
        for charts whose data is a URL, or that concatenate charts with
        different data. Returns an empty frame while nothing is selected. Dates
        are compared in UTC, reading time-zone-naive columns in the browser's
        time zone, as Vega-Lite does.
        """
        selection = self.selected(name)
        widget = cast(JupyterChart, self._widget)
        frame = chart_frame(widget) if df is None else df
        return filter_selection(selection, frame, widget.local_tz)


class render_embedding_atlas(
    render_widget_base[EmbeddingAtlasWidget, EmbeddingAtlasWidget]
):
    """
    Reactively render an [Embedding Atlas](https://apple.github.io/embedding-atlas/)
    explorer as a Shiny output.

    The decorated function should return an `embedding_atlas.widget.EmbeddingAtlasWidget`
    (requires ``pip install 'shinywidgets[embedding_atlas]'``, which needs Python 3.11
    or newer).
    Unlike the other decorators, a bare data frame isn't enough to build the widget, so
    construct it yourself, passing the data frame along with the columns that describe
    the embedding (e.g., ``EmbeddingAtlasWidget(df, x="x", y="y", text="text")``).
    The embedding (scatter) view itself requires a browser with WebGPU and its
    ``shader-f16`` feature (e.g., recent Chrome, Edge, or Firefox); elsewhere, the
    rest of the explorer still works. The explorer needs room: in a non-filling
    layout, give the output a height of at least ``"600px"``.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `EmbeddingAtlasWidget` instance. The filter a user builds in the browser is
    synced to the widget's (upstream-internal) `_predicate` trait, so
    ``reactive_read(my_atlas.widget, "_predicate")`` followed by
    ``my_atlas.widget.selection()`` gives the selected rows reactively. The explorer
    doesn't respond to trait changes made from Python; to change it, re-render.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Note
    ---
    **Security**: the explorer runs its queries by sending SQL from the browser to
    the widget's DuckDB connection, and without restrictions any visitor can send
    arbitrary SQL, including SQL that reads or writes files on the server. To
    protect against this, the renderer locks down the widget's connection before
    display (``SET enable_external_access = false``; ``SET lock_configuration =
    true``), so that only the data you gave the widget is reachable. If you locked
    the connection's configuration yourself (``SET lock_configuration = true``),
    the renderer leaves your configuration untouched. Pass
    ``allow_unrestricted_connection=True`` to opt out of the lockdown (e.g., for a
    local, single-user app).

    Even with the lockdown, a visitor can still send expensive queries, which
    block the Python process while they run.

    Parameters
    ----------
    allow_unrestricted_connection
        When ``True``, the widget's DuckDB connection is left as the render
        function returned it, without the lockdown described above. The default
        (``False``) is strongly recommended for deployed apps: an unrestricted
        connection lets any visitor run arbitrary SQL with the server process's
        permissions.
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    def __init__(
        self,
        _fn: Optional[ValueFn[EmbeddingAtlasWidget]] = None,
        *,
        width: Optional[str] = None,
        height: Optional[str] = None,
        fill: Optional[bool] = None,
        fillable: Optional[bool] = None,
        rate_policy: Optional[RatePolicy] = None,
        rate_delay: Optional[float] = None,
        allow_unrestricted_connection: bool = False,
    ):
        super().__init__(
            _fn,
            width=width,
            height=height,
            fill=fill,
            fillable=fillable,
            rate_policy=rate_policy,
            rate_delay=rate_delay,
        )
        self.allow_unrestricted_connection = allow_unrestricted_connection

    def _as_widget(self, value: EmbeddingAtlasWidget) -> EmbeddingAtlasWidget:
        widget = super()._as_widget(value)
        if not self.allow_unrestricted_connection:
            restrict_embedding_atlas_connection(widget)
        return widget


def restrict_embedding_atlas_connection(widget: EmbeddingAtlasWidget) -> None:
    """
    Lock down an `EmbeddingAtlasWidget`'s DuckDB connection, so the SQL the
    browser sends can't reach server files or change the connection's
    configuration.
    """
    # `_connection` is upstream-internal (like the `_predicate` trait this
    # renderer already relies on); embedding-atlas is pre-1.0, so fail loudly if
    # it disappears rather than silently render an unrestricted widget.
    con = getattr(widget, "_connection", None)
    if con is None:
        raise RuntimeError(
            "Couldn't find the EmbeddingAtlasWidget's DuckDB connection "
            "(`_connection`), so its SQL access can't be restricted. If "
            "embedding-atlas renamed this attribute, please report it. To render "
            "anyway, pass `allow_unrestricted_connection=True` to "
            "`@render_embedding_atlas`."
        )
    restrict_duckdb_connection(con)


def duckdb_settings(
    con: Optional[duckdb.DuckDBPyConnection] = None,
) -> Tuple[bool, bool]:
    """
    DuckDB's ``(enable_external_access, lock_configuration)`` for `con`, which
    defaults to the default connection.
    """
    import duckdb  # pyright: ignore[reportMissingImports]

    target = duckdb if con is None else con
    settings = target.execute(
        "SELECT current_setting('enable_external_access'),"
        " current_setting('lock_configuration')"
    ).fetchone()
    assert settings is not None  # the query always returns its two settings
    external_access, locked = settings
    return bool(external_access), bool(locked)


def restrict_duckdb_connection(con: duckdb.DuckDBPyConnection) -> None:
    """
    Lock down a DuckDB connection, so SQL run on it can't reach server files or
    change the connection's configuration. A connection whose configuration is
    already locked is left untouched: its owner took control of its settings
    (possibly keeping external access on deliberately), and a locked connection
    rejects further SET commands.
    """
    if duckdb_settings(con)[1]:
        return
    con.execute("SET enable_external_access = false")
    con.execute("SET lock_configuration = true")


class render_ipyaladin(render_widget_base[ValueT, Aladin]):
    """
    Reactively render an [ipyaladin](https://cds-astro.github.io/ipyaladin/) sky
    viewer (Aladin Lite) as a Shiny output.

    The decorated function should return an `ipyaladin.Aladin` widget (requires
    ``pip install 'shinywidgets[ipyaladin]'``). In a filling layout, the viewer
    fills its container unless the `Aladin` has an explicit ``height`` (or its
    ``layout`` has an explicit height).

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `Aladin` instance. Use `.widget` to programmatically update the rendered
    viewer in place (e.g., ``.widget.target = "M31"`` or ``.widget.fov = 5``;
    trait changes on the widget are synced to the browser), or to reactively read
    viewer state with :func:`~shinywidgets.reactive_read`.

    Note
    ---
    **Reactive state**: the viewer's center and field of view are synced from the
    browser to the ``_target`` (a ``"ra dec"`` string, in degrees) and ``_fov``
    (degrees) traits, so panning or zooming the sky can drive a reactive
    calculation (e.g., ``reactive_read(sky.widget, "_target")``). The public
    ``.target``/``.fov`` properties (an astropy `SkyCoord`/`Angle`) parse these
    traits, but are not themselves traits, so they can't be read reactively.

    **Updating in place**: ipyaladin queues method calls (e.g.,
    ``.widget.add_table()``) until the viewer has loaded in the browser, but
    property assignments (e.g., ``.widget.fov = 5``) are not queued, so gate
    effects that set them on ``reactive_read(sky.widget, "_is_loaded")``. Don't
    gate on the ``_ready`` trait instead: ipyaladin 0.8.1 never sets it.

    **Interacting with catalogs**: clicking a catalog source syncs it to the
    ``clicked_object`` trait, and box-selecting
    (``.widget.selection("rectangle")``) syncs the sources inside to
    ``_selected_objects`` — both work with
    :func:`~shinywidgets.reactive_read`. Prefer these traits over
    ``.widget.set_listener()``: in ipyaladin 0.8.x listener callbacks are
    shared across all `Aladin` instances, so they are not session-safe in a
    multi-user Shiny app. When setting ``.widget.target`` in place, use a
    ``"ra dec"`` string or an astropy `SkyCoord` (a plain float tuple raises
    in ipyaladin's setter).

    **Network access**: the viewer loads its JavaScript from a CDN and its sky
    imagery (HiPS tiles) from CDS servers at render time, so it requires an
    internet connection.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """


class render_ipyleaflet(render_widget_base[ValueT, LeafletMap]):
    """
    Reactively render an [ipyleaflet](https://ipyleaflet.readthedocs.io) map as a Shiny
    output.

    The decorated function should return an `ipyleaflet.Map` (requires ``pip install
    ipyleaflet``) or a subclass of it, such as a `leafmap.leafmap.Map`.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `Map` instance. Use `.widget` to programmatically update the rendered map in
    place (e.g., change its `zoom` or `center`, or add layers; trait changes on the
    widget are synced to the browser), or to reactively read map state (e.g., `zoom`,
    `center`, `bounds`) with :func:`~shinywidgets.reactive_read`.

    In a filling layout, the map fills its container unless it has its own height
    (e.g., ``Layout(height="300px")``). Default heights set by a subclass (e.g.,
    leafmap's 600px) are treated as unset.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """


class render_ipysigma(render_widget_base[ValueT, Sigma]):
    """
    Reactively render a graph with [ipysigma](https://github.com/medialab/ipysigma)
    (sigma.js) as a Shiny output.

    The decorated function may return either a networkx graph (which is coerced to an
    `ipysigma.Sigma` widget with default options; requires ``pip install
    'shinywidgets[ipysigma]'``) or an `ipysigma.Sigma` widget, which is the way to
    customize node and edge appearance (e.g., `Sigma(G, node_size=G.degree,
    node_color="community")`). This is also the answer for
    [pyvis](https://pyvis.readthedocs.io) users: ipysigma renders larger
    networks more smoothly and, being a widget, can report the selected node back to
    Python. In a filling layout, the graph fills its container, unless the widget has
    an explicit `height` or `raw_height` (a height of 500px, sigma's default, or one set
    globally with `Sigma.set_defaults(height=...)`, counts as unset and fills).

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `Sigma` instance. Use `.widget` to reactively read the user's interactions with
    :func:`~shinywidgets.reactive_read` (e.g., ``reactive_read(sigma.widget,
    "selected_node")``; also ``"selected_edge"``, ``"camera_state"`` and
    ``"layout"``). Note that ipysigma only reads its options when the graph is
    first drawn, so setting traits on `.widget` afterwards does not update the
    browser. To change what's shown, re-render, passing any state you want to keep
    (e.g., ``layout=``, ``camera_state=``) to the new `Sigma`.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    def _as_widget(self, value: ValueT) -> Sigma:
        if isinstance(value, Widget):
            return super()._as_widget(value)
        return networkx_to_sigma(value)


class render_itables(render_widget_base[ValueT, ITable]):
    """
    Reactively render a [pandas](https://pandas.pydata.org) or
    [polars](https://pola.rs) data frame as an interactive
    [itables](https://itables.org) (DataTables) Shiny output.

    The decorated function may return either a data frame (which is coerced to an
    `itables.widget.ITable`) or an `itables.widget.ITable` widget, which is how to
    pass itables options such as ``select=True`` (requires ``pip install
    'shinywidgets[itables]'``).

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `ITable` instance. Use ``.selected_rows()`` to reactively read the selected
    rows, or `.widget` to programmatically update the rendered table
    in place (trait changes on the widget are synced to the browser), or to
    reactively read widget state (e.g., `selected_rows`) with
    :func:`~shinywidgets.reactive_read`.

    In a filling layout, the table fills its container and scrolls its rows; give it
    roughly 350px or more of height, since smaller containers leave no room for rows
    below DataTables' controls. Some itables defaults worth knowing about:

    * Columns sort when their arrow icon is clicked (header text is selectable); pass
      ``text_in_header_can_be_selected=False`` to sort on any header click.
    * Data frames larger than itables' ``maxBytes`` (64KB by default) are downsampled;
      pass ``maxBytes=0`` to send all rows.
    * `selected_rows` holds row positions in the current data frame.
      ``ITable.update(df)`` keeps those positions as-is, and drops options such as
      ``columnDefs`` and ``buttons`` unless they are passed again.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    rate_policy
        How to rate-limit :func:`~shinywidgets.reactive_read` on the widget:
        ``"debounce"`` or ``"throttle"``. ``None`` (the default) leaves
        ``reactive_read()`` unlimited.
    rate_delay
        The rate-limit window in milliseconds (default 250). ``0`` disables rate
        limiting.
    """

    accessor_specs = ITABLES_ACCESSORS

    def selected_rows(self) -> List[int]:
        """
        The currently selected rows as a list of positions into the table's
        data frame (use ``df.iloc[table.selected_rows()]``), or ``[]`` while
        nothing is selected.

        Positions are in data order, not display order: they survive sorting
        and searching, and the same position can refer to a different row
        after ``.widget.update(df)``. Requires ``select=True`` on the
        `itables.widget.ITable` (a plain data frame return has no selection).
        Not rate-limited.
        """
        return cast(List[int], self._read_accessor("selected_rows"))

    def _as_widget(self, value: ValueT) -> ITable:
        if isinstance(value, Widget):
            return super()._as_widget(value)
        try:
            from itables.widget import ITable
        except ImportError:
            raise ImportError(
                "Install the itables package to use data frames with shinywidgets "
                "(pip install 'shinywidgets[itables]')."
            )
        return ITable(value)


class render_jscatter(render_widget_base[ValueT, JupyterScatter]):
    """
    Reactively render a [jupyter-scatter](https://jupyter-scatter.dev) scatter plot as a
    Shiny output.

    The decorated function may return a `jscatter.Scatter` (which is coerced to its
    `jscatter.widget.JupyterScatter` widget; requires ``pip install 'shinywidgets[jscatter]'``)
    or a `JupyterScatter` widget. The plot is resized to fit its output, whether the
    output fills its layout or has an explicit ``height`` (see below), unless the plot
    has a height of its own (e.g., from `Scatter.height()`; jupyter-scatter's default of
    240 doesn't count).

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `JupyterScatter` instance. Use ``.selection()`` to reactively read the selected
    points (below), or `.widget` to programmatically update the rendered plot in
    place (trait changes on the widget are synced to the browser), or to reactively
    read widget state (e.g., the selected points via ``"selection"``) with
    :func:`~shinywidgets.reactive_read`. The selection is an array of row *positions*
    (use ``df.iloc[...]``), not index labels.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Note
    ---
    **Reacting to selections**: read ``plot.selection()`` in a reactive function (a
    ``@render.*`` function, ``@reactive.calc``, or ``@reactive.effect``), which
    re-runs whenever the user selects points (with the lasso, or by clicking one),
    much like ``input.my_slider()`` reads an input. A re-render (e.g. when the
    render function reads an input) gives the user a new plot, whose selection
    starts out empty. It can't be read inside this output's own render function,
    which builds a new plot each time it runs.

    **Large selections**: selecting more than about 3 million points sends the
    server a message larger than the default 16 MiB websocket limit, which
    disconnects the session. Raise the limit with ``shiny run --ws-max-size``.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    rate_policy
        How to rate-limit :func:`~shinywidgets.reactive_read` on the widget:
        ``"debounce"`` or ``"throttle"``. ``None`` (the default) leaves
        ``reactive_read()`` unlimited.
    rate_delay
        The rate-limit window in milliseconds (default 250). ``0`` disables rate
        limiting.
    """

    accessor_specs = JSCATTER_ACCESSORS

    def selection(self) -> "np.ndarray":
        """
        The currently selected points as a `numpy.ndarray` (uint32) of row
        *positions* into the plot's data (use ``df.iloc[plot.selection()]``),
        from a lasso or single click.

        Empty while nothing is selected. Cancels (like `.widget`) until the
        browser first reports, which a bare `JupyterScatter` only does after
        the first selection. For index labels instead of positions (when the
        render function returns a `jscatter.Scatter` with
        ``data_use_index=True``), use ``plot.value.selection()``.
        Not rate-limited.
        """
        return cast("np.ndarray", self._read_accessor("selection"))


class render_k3d(render_widget_base[ValueT, K3dPlot]):
    """
    Reactively render a [k3d](https://k3d-jupyter.org) 3D plot as a Shiny output.

    The decorated function should return a `k3d.Plot` (i.e., the result of
    `k3d.plot()` with objects added to it; requires ``pip install 'shinywidgets[k3d]'``),
    or a bare k3d object such as `k3d.points(...)`, which is placed on a new plot. By
    default, the plot fills its container; pass `height` to `k3d.plot()` to use a fixed
    pixel height instead (a `height` of 512, the k3d default, is treated as unspecified).

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `Plot` instance. Use `.widget` to programmatically update the rendered plot in
    place (trait changes on the widget are synced to the browser), or to reactively
    read widget state with :func:`~shinywidgets.reactive_read`.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    def _as_widget(self, value: ValueT) -> K3dPlot:
        try:
            # Import the factory from its own module: `k3d.plot` is also the name of
            # the submodule defining Plot, which is what type checkers resolve
            from k3d.factory.plot import plot as new_plot
            from k3d.objects import Drawable
        except ImportError:
            raise ImportError(
                "Install the k3d package to use render_k3d with shinywidgets (pip install 'shinywidgets[k3d]')."
            )

        # A drawable is a model-only widget that draws nothing by itself, so (like
        # its Jupyter display does) put it on a new plot
        if isinstance(value, Drawable):
            plot = new_plot()
            plot += value
            # k3d annotates `+=` as returning its PlotObjectsMixin, but it returns self
            return cast(K3dPlot, plot)
        return cast(K3dPlot, super()._as_widget(value))


class render_ipycytoscape(render_widget_base[ValueT, CytoscapeWidget]):
    """
    Reactively render an [ipycytoscape](https://github.com/cytoscape/ipycytoscape)
    network graph as a Shiny output.

    The decorated function may return either a `networkx.Graph` (which is coerced to
    an `ipycytoscape.CytoscapeWidget`; requires ``pip install 'shinywidgets[ipycytoscape]'``)
    or an
    `ipycytoscape.CytoscapeWidget` widget.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `CytoscapeWidget` instance. Use `.widget` to update the graph in place (e.g.,
    `.widget.set_style()`, `.widget.set_layout()`, or setting `classes` on the nodes
    in `.widget.graph.nodes`) without re-rendering.

    To react to user interaction, register callbacks with `CytoscapeWidget.on()`
    inside the render function, before returning the widget, and have them set a
    :class:`~shiny.reactive.value`. (ipycytoscape drops some callbacks registered
    after the graph is displayed, e.g. from an effect: only the first event type
    per element type is wired up.) Node selection is also synced to each node's
    `selected` trait, readable with :func:`~shinywidgets.reactive_read`, but
    ipycytoscape makes nodes unselectable by default: create the widget with
    `auto_unselectify=False` and set `selectable = True` on each node (plus
    `box_selection_enabled=True` for shift-drag selection).

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    def _as_widget(self, value: ValueT) -> CytoscapeWidget:
        # A networkx graph is a generic type (render_ipysigma accepts one too), so
        # it's coerced here rather than registered in AS_WIDGET_MAP
        if is_networkx_graph(value):
            return networkx_to_cytoscape(value)
        return cast(CytoscapeWidget, super()._as_widget(value))


def is_networkx_graph(value: object) -> bool:
    try:
        from networkx import Graph
    except ImportError:
        return False
    return isinstance(value, Graph)


def networkx_to_cytoscape(graph: object) -> CytoscapeWidget:
    try:
        from ipycytoscape import CytoscapeWidget as Widget
    except ImportError:
        raise ImportError(
            "Install the ipycytoscape package to use networkx graphs with shinywidgets (pip install 'shinywidgets[ipycytoscape]')."
        )

    res = Widget()
    res.graph.add_graph_from_networkx(graph)
    return res


class render_bqplot(render_widget_base[ValueT, BqplotFigure]):
    """
    Reactively render a [bqplot](https://bqplot.github.io/bqplot/) figure as a Shiny
    output.

    The decorated function should return a `bqplot.Figure`, including one created
    through the `bqplot.pyplot` interface (requires ``pip install 'shinywidgets[bqplot]'``).

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `Figure` instance. Use `.widget` to programmatically update the rendered figure
    in place (trait changes on the widget are synced to the browser), or to
    reactively read widget state with :func:`~shinywidgets.reactive_read`.

    When using `bqplot.pyplot`, start the render function with
    ``fig = bplt.figure(...)`` and return ``fig``. pyplot's "current figure" is global
    to the Python process, so plotting without ``bplt.figure()`` (or with
    ``bplt.figure(key=...)``) reuses one figure across renders, outputs and sessions,
    which fails after the first re-render.

    The figure's built-in toolbar (``display_toolbar=True``) and a standalone
    ``bqplot.Toolbar`` work, and the active ``PanZoom`` is readable with
    ``reactive_read(fig.widget, "interaction")``.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """


class render_geolibre(render_widget_base[GeolibreMap, GeolibreMap]):
    """
    Reactively render a [GeoLibre](https://geolibre.app) map -- the full
    GeoLibre GIS app embedded as a widget -- as a Shiny output.

    The decorated function should return a `geolibre.Map` (requires
    ``pip install 'shinywidgets[geolibre]'``). In a filling layout, the map
    fills its container unless the `Map` was given a ``height`` other than
    geolibre's default (``"800px"``). The ``height`` is read once, when the
    embedded app loads, so changing ``.widget.height`` after rendering has no
    effect (resize the output's container instead).

    The decorated function also gains two read-only attributes: `.value` and
    `.widget`, both the rendered `geolibre.Map` instance. Use `.widget` to
    update the rendered map in place, or to reactively read its state.

    Note
    ---
    **Updating the map from Python**: methods that edit the map's *project*
    (its synced document) work as they do in Jupyter --
    ``add_geojson()``/``add_vector()``/``add_cog()``/etc.,
    ``set_center()``/``set_zoom()``/``fit_project_bounds()``, layer styling
    (``get_layer(id).set_style()``/``set_opacity()``), and
    ``set_identify()``/``show_control()``. Methods that send a command to the
    app and block waiting for its reply can never work on Shiny's event-loop
    thread -- not directly inside a render function, `reactive.calc`, or a
    `reactive.effect`/observer (sync or async) -- because the wait would
    block the very loop that must deliver the reply. These include
    ``fly_to()``, ``fit_bounds()``, ``zoom_to_layer()``, ``identify()``,
    ``get_center()``/``get_view()``/``get_bounds()``,
    ``get_selected_features()``/``get_drawn_features()``, ``run_algorithm()``,
    and ``to_image()``. They do work from a worker thread (where the event
    loop stays free), e.g., inside `reactive.extended_task` via
    ``asyncio.get_running_loop().run_in_executor(None, map.widget.fly_to, ...)``
    -- geolibre >= 3.5.2 (enforced by the ``shinywidgets[geolibre]`` extra)
    polls for the reply instead of pumping a Jupyter kernel event loop, so
    these work in Shiny from a worker thread. Where a non-blocking
    alternative exists -- ``set_center()`` for ``fly_to()``,
    ``fit_project_bounds()`` for ``fit_bounds()``, the synced ``project``
    trait for the query methods -- it remains the cheaper option.

    **Reading map state**: user edits in the app (panning, zooming, adding or
    restyling layers) sync back to the ``project`` trait, so
    ``reactive_read(map.widget, "project")`` gives you the live project --
    but note it invalidates on every pan and zoom, and carries the whole
    project (including inlined layer data), so prefer the event callbacks for
    high-frequency interactions: register ``map.widget.on_click()``,
    ``on_selection_change()``, or ``on_layer_change()`` inside the render
    function and have the callback set a `reactive.value`.

    **Network access**: shinywidgets serves the bundled GeoLibre app from the
    Shiny app itself, so the widget works in deployed apps (shinyapps.io,
    Posit Connect, ...) as well as locally. This includes layers read from
    files on the server's disk (e.g., ``add_cog()``/``add_raster()`` of a
    local GeoTIFF): geolibre serves those from a localhost server in the
    Python process, and shinywidgets mounts a reverse proxy at
    ``/proxy/{port}/`` that forwards that server to the browser, same-origin
    (the same role jupyter-server-proxy plays for Jupyter servers). Note this
    makes the localhost server reachable by anyone who can reach the app;
    its file routes are protected by unguessable per-process tokens. Basemap
    tiles and remote data URLs require internet access from the browser.

    **The ``layout`` parameter**: `geolibre.Map(layout=...)` chooses the
    app's chrome (``"embed"``, ``"full"``, or ``"maponly"``); it is *not*
    an `ipywidgets.Layout`, so ipywidgets layout styling (e.g.,
    ``Layout(border=...)``) isn't available on this widget. (geolibre
    reuses the ``layout`` trait name, which also causes a harmless
    "Cannot read properties of undefined" error in the browser console.)

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """


class render_keplergl(render_widget_base[ValueT, KeplerGl]):
    """
    Reactively render a [kepler.gl](https://kepler.gl) map as a Shiny output.

    The decorated function may return either a `pandas.DataFrame` or
    `geopandas.GeoDataFrame` (which is coerced to a `keplergl.KeplerGl` widget with
    the data added as a single dataset named ``"data"``, the ``dataId`` to use in a
    kepler.gl ``config``; requires ``pip install 'shinywidgets[keplergl]'``) or a
    `keplergl.KeplerGl` widget. In a filling layout, the map is resized to fit its
    container, unless the `KeplerGl` widget was given a ``height`` other than
    kepler.gl's default (400). An explicit ``height`` on the output (see ``height``
    below) takes precedence over the widget's own. While the output sizes the map,
    the browser sets the widget's ``height`` to the size it measures, so change the
    output's size rather than setting the widget's ``height`` from Python.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `KeplerGl` instance. Use `.widget` to programmatically update the rendered map
    in place (trait changes on the widget are synced to the browser), or to
    reactively read widget state with :func:`~shinywidgets.reactive_read`.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    def _as_widget(self, value: ValueT) -> KeplerGl:
        # A DataFrame is generic (several renderers accept one), so it's only
        # coerced here rather than via AS_WIDGET_MAP
        # (Only import pandas, an optional dependency, if it's already in use)
        if "pandas" in sys.modules:
            import pandas as pd

            if isinstance(value, pd.DataFrame):
                return dataframe_to_keplergl(value)
        return super()._as_widget(value)


class render_ipyvolume(render_widget_base[ValueT, IpyvolumeFigure]):
    """
    Reactively render an [ipyvolume](https://ipyvolume.readthedocs.io) 3D plot as
    a Shiny output.

    The decorated function may return an `ipyvolume.Figure` widget (requires
    ``pip install 'shinywidgets[ipyvolume]'``; ipyvolume 0.6.3 also needs
    ``ipython_genutils``, which it doesn't declare, so the extra installs it
    for you). Both ways of getting one work: the pylab API (return `ipv.gcf()`
    after drawing, or the container returned by `ipv.quickscatter()`/
    `ipv.gcc()`, which is unwrapped to its figure) or direct construction
    (`ipyvolume.Figure`, with `ipyvolume.widgets.Scatter` and friends added to
    ``fig.scatters``). Either way, call the constructors inside the render
    function: the pylab functions draw on a module-level "current figure", so
    figures created elsewhere can end up shared across sessions. With direct
    construction, set ``size_selected``/``color_selected`` explicitly on
    scatters -- their trait defaults are 0-d numpy arrays, which don't
    JSON-serialize -- and set ``fig.xlim``/``fig.ylim``/``fig.zlim``, since
    directly constructed figures default to a [0, 1]^3 axis box with no
    auto-fit. In a filling layout, the figure's WebGL canvas is resized to
    fill its container (and tracks container resizes) unless the figure has
    an explicit ``width`` or ``height``.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `ipyvolume.Figure` instance. Use `.widget` to programmatically update the
    rendered figure in place (trait changes on the widget are synced to the
    browser), or to reactively read widget state with
    :func:`~shinywidgets.reactive_read` (e.g., ``reactive_read(plot.widget,
    "camera")``). For selections, register a callback with
    ``plot.widget.on_selection(fn)`` (selections arrive as custom messages, not
    trait changes) and set a `reactive.value` inside it.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Examples
    --------
    ```python
    import ipyvolume as ipv
    import numpy as np
    from shiny import App, ui
    from shinywidgets import output_widget, render_ipyvolume

    app_ui = ui.page_fillable(output_widget("plot"))


    def server(input, output, session):
        @render_ipyvolume
        def plot():
            x, y, z = np.random.normal(size=(3, 1000))
            ipv.quickscatter(x, y, z, size=1, marker="sphere")
            return ipv.gcf()


    app = App(app_ui, server)
    ```
    """


class render_leafmap(render_widget_base[ValueT, LeafletMap]):
    """
    Reactively render a [leafmap](https://leafmap.org) map as a Shiny output.

    leafmap (requires ``pip install 'shinywidgets[leafmap]'``) is a high-level API
    over several mapping engines. Return any of its widget-backed backends:

    * `leafmap.leafmap.Map` (the default; an `ipyleaflet.Map`) -- includes
      leafmap's toolbar, basemap gallery, legends, and its other tools. This is
      the backend to start with.
    * `leafmap.maplibregl.Map` (a maplibre `MapWidget`) -- vector tiles, globe
      projection, and deck.gl layers via `add_deck_layers()`.
    * `leafmap.plotlymap.Map` (a Plotly `FigureWidget`) -- Plotly map traces
      and in-place updates through `set_center()` and `update_traces()`.
      Requires Plotly >=5.12 and <7, included in the leafmap extra.
    * `leafmap.kepler.Map` (a kepler.gl widget) -- kepler.gl's layer/filter UI,
      including time playback. Keep in mind that its `config` trait nests
      kepler's own config (e.g., ``config["config"]["mapState"]``).

    leafmap's folium (``leafmap.foliumap.Map``) and pydeck (``leafmap.deck.Map``)
    backends aren't ipywidgets, so they raise a `TypeError` that points to
    alternatives.

    Maps fill their container, including in a non-filling ``page_*()``, unless the
    map has a height of its own (e.g., ``leafmap.Map(height=400)``, or
    ``Layout(height="300px")``). leafmap's 600px default is treated as unset.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    widget. Use `.widget` to programmatically update the rendered map in place
    (e.g., change its `zoom` or `center`, or add layers; trait changes on the
    widget are synced to the browser), or to reactively read map state with
    :func:`~shinywidgets.reactive_read`, e.g. ``zoom``/``center``/``bounds`` for
    the ipyleaflet backend, or ``view_state``/``clicked`` for the maplibre one.
    The Plotly backend is already a `FigureWidget`, so it is rendered directly;
    `.value` retains the original map and its leafmap methods.

    Note
    ----
    **Typing**: `.widget` is typed as an `ipyleaflet.Map` (the default backend,
    and what `leafmap.leafmap.Map` subclasses), so it type-checks best with that
    backend. For another backend, `.widget` is that backend's widget at runtime.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """


class render_lonboard(render_widget_base[ValueT, LonboardMap]):
    """
    Reactively render a [lonboard](https://developmentseed.org/lonboard/) map as a
    Shiny output.

    The decorated function may return a `lonboard.Map` widget, a lonboard layer (or a
    list of layers), which is placed on a `Map`, or any data that `lonboard.viz()`
    accepts (e.g., a GeoPandas `GeoDataFrame` or a GeoArrow-compatible Arrow table),
    which is converted to a `Map` via `lonboard.viz()` (requires ``pip install
    'shinywidgets[lonboard]'``). In a filling layout, the map fills its container
    unless the `Map`
    has an explicit ``height``.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered `Map`
    instance. Use `.widget` to programmatically update the rendered map in place
    (trait changes on the widget are synced to the browser), or to reactively read
    widget state with :func:`~shinywidgets.reactive_read`.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    def _as_widget(self, value: ValueT) -> LonboardMap:
        if isinstance(value, Widget):
            return super()._as_widget(value)

        try:
            import lonboard  # pyright: ignore[reportMissingImports]
        except ImportError:
            raise ImportError(
                "Install the lonboard package to use render_lonboard with shinywidgets (pip install 'shinywidgets[lonboard]')."
            )

        # viz() handles lists of data, but not lists of layers
        if isinstance(value, (list, tuple)) and all(
            isinstance(x, lonboard.BaseLayer) for x in value
        ):
            m = lonboard.Map(value)
        else:
            m = lonboard.viz(value)
        return super()._as_widget(cast(ValueT, m))


class render_ipycanvas(render_widget_base[IpycanvasCanvasT, IpycanvasCanvasT]):
    """
    Reactively render an [ipycanvas](https://ipycanvas.readthedocs.io) canvas as a
    Shiny output.

    The decorated function may return an `ipycanvas.Canvas`, `ipycanvas.MultiCanvas`,
    `ipycanvas.RoughCanvas`, or `ipycanvas.MultiRoughCanvas` widget (requires ``pip
    install 'shinywidgets[ipycanvas]'``). The canvas keeps its pixel ``width``/``height`` (which are
    drawing-buffer sizes, not layout sizes): in a filling layout the output fills its
    container and the canvas is centered within it (shrinking to fit, aspect
    preserved), never stretched. Size the canvas through the constructor's
    ``width``/``height``, not ``widget.layout.height`` -- a Layout height opts out of
    filling, and since the buffer pixels are fixed, the browser can only rescale the
    existing bitmap to fit.

    The decorated function also gains two read-only attributes: `.value` and
    `.widget`, both the rendered canvas. Draw on `.widget` from anywhere (e.g., a
    `reactive.effect` or an `asyncio` task) and the browser canvas updates in
    place. Use `.widget` to reactively read widget state with
    :func:`~shinywidgets.reactive_read`, or register event callbacks like
    ``on_mouse_down()``/``on_mouse_move()`` that set `reactive.value`s. With
    shiny < 1.9, canvas updates made from a background task may not reach the
    browser until the next input event. Note that ``ipycanvas.hold_canvas()``
    has no effect under shinywidgets (each draw command is sent individually).

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Examples
    --------
    ```python
    from ipycanvas import Canvas
    from shiny import App, ui
    from shinywidgets import output_widget, render_ipycanvas

    app_ui = ui.page_fluid(output_widget("canvas"))


    def server(input, output, session):
        @render_ipycanvas
        def canvas():
            c = Canvas(width=300, height=200)
            c.fill_style = "steelblue"
            c.fill_rect(20, 20, 100, 100)
            return c


    app = App(app_ui, server)
    ```
    """


class render_maplibre(render_widget_base[MaplibreValueT, MapWidget]):
    """
    Reactively render a [maplibre](https://eoda-dev.github.io/py-maplibregl/) map as a
    Shiny output.

    The decorated function may return either a `maplibre.Map` (which is coerced to a
    `maplibre.ipywidget.MapWidget`; requires ``pip install 'shinywidgets[maplibre]'``)
    or a `maplibre.ipywidget.MapWidget` widget. In a filling layout, the map fills
    its container unless the `MapWidget` has an explicit ``height``.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `MapWidget` instance. To update the rendered map in place, call methods on
    `.widget` (e.g., `set_paint_property()`, `set_filter()`, `set_data()`,
    `fit_bounds()`, or `add_call()` for any MapLibre GL JS map method). These are sent
    to the browser as commands, so assigning traits such as `map_options` after
    rendering has no effect. To reactively read map state, use
    :func:`~shinywidgets.reactive_read` with `view_state` (center, zoom, bounds,
    bearing, and pitch), `clicked` (the longitude and latitude of the last click), or
    the MapboxDraw ``draw_*`` traits. Feature-level click and hover events aren't
    synced.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """


class render_matplotlib(render_widget_base[ValueT, MplCanvas]):
    """
    Reactively render a [matplotlib](https://matplotlib.org) figure as an interactive
    [ipympl](https://matplotlib.org/ipympl/) Shiny output.

    The decorated function may return a `matplotlib.figure.Figure`, a
    `matplotlib.axes.Axes` (rendered via its figure), or an `ipympl.backend_nbagg.Canvas`
    widget. Figures and axes are coerced to a `Canvas` (requires ``pip install
    'shinywidgets[matplotlib]'``),
    so this also works with libraries built on matplotlib (e.g., seaborn or
    ``pandas.DataFrame.plot()``). In a filling layout, the figure is resized to fit its
    container. With an explicit ``height``, the figure keeps its ``figsize`` unless the
    output is also ``fillable=True``.

    Unlike `@render.plot`, which draws a static image, the figure stays alive on the
    server for as long as it is displayed, so it can respond to the user. Like
    `@render.plot`, a figure created through pyplot is closed (as by ``plt.close()``)
    once it's rendered. Still, prefer creating figures explicitly (e.g.,
    ``Figure(layout="constrained")`` or ``plt.subplots()``) over pyplot's implicit
    current figure or axes (``plt.plot()``, ``plt.gca()``, or seaborn functions without
    ``ax=``), which are shared by every output and session in the process.

    Create figures with a non-interactive backend: ``matplotlib.figure.Figure()``
    directly, or pyplot under the ``agg`` backend (the default when no display is
    available, as on a server; select it locally with ``matplotlib.use("agg")``
    before creating figures). A figure created under a GUI backend (Qt, Tk, macOS,
    ...) can still be rendered -- its window is destroyed and ipympl's canvas
    replaces its own -- but that path depends on platform-specific behavior that
    automated tests can't exercise, so it is supported on a best-effort basis and
    warns at render time.

    Browser interactions reach Python through matplotlib's own callbacks, e.g.,
    ``fig.canvas.mpl_connect("button_press_event", f)`` or
    ``ax.callbacks.connect("xlim_changed", f)`` (which fires on every zoom and pan). To
    make other outputs respond, set a `reactive.value` from the callback.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `Canvas` instance. To update the rendered figure without losing the user's zoom,
    modify the artists of ``.widget.figure`` and call ``.widget.draw_idle()``.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Examples
    --------
    ```python
    from matplotlib.figure import Figure
    from shiny import App, reactive, render, ui
    from shinywidgets import output_widget, render_matplotlib

    app_ui = ui.page_fluid(
        ui.input_slider("n", "Points", 10, 100, 50),
        output_widget("plot"),
        ui.output_text("visible"),
    )


    def server(input, output, session):
        xlim = reactive.value((0.0, 0.0))

        @render_matplotlib
        def plot():
            fig = Figure(layout="constrained")
            ax = fig.subplots()
            ax.plot(range(input.n()))
            ax.callbacks.connect("xlim_changed", lambda ax: xlim.set(ax.get_xlim()))
            return fig

        @render.text
        def visible():
            lo, hi = xlim()
            return f"Showing x from {lo:.1f} to {hi:.1f}"


    app = App(app_ui, server)
    ```
    """


class render_nglview(render_widget_base[ValueT, NGLWidget]):
    """
    Reactively render an [nglview](https://nglviewer.org/nglview/latest/) molecular
    structure viewer as a Shiny output.

    The decorated function should return an `nglview.NGLWidget` (e.g., from
    `nglview.show_file()`, `nglview.show_text()`, or `nglview.show_url()`; requires
    ``pip install 'shinywidgets[nglview]'``).

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `NGLWidget` instance. Use `.widget` to programmatically update the rendered viewer
    in place (trait changes on the widget are synced to the browser), or to
    reactively read widget state with :func:`~shinywidgets.reactive_read` (e.g., the
    picked atom via ``"picked"``).

    Changes made with `.widget` methods (e.g., `add_representation()`,
    `center()`, `clear_representations()`) reach the browser even though
    nglview sends them from a background thread (requires shiny >= 1.9).

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """


class render_mosaic_widget(render_widget_base[MosaicWidget, MosaicWidget]):
    """
    Reactively render a [Mosaic](https://idl.uw.edu/mosaic/) dashboard of linked,
    DuckDB-backed views as a Shiny output.

    The decorated function should return a `mosaic_widget.MosaicWidget` (requires
    ``pip install 'shinywidgets[mosaic_widget]'``), built from a Mosaic spec and
    the data (e.g., a DataFrame) to register with DuckDB. Mosaic specs set the size of each plot, so
    the plots keep those pixel sizes while the output itself fills its container
    (or takes the explicit ``height``). With an explicit ``height`` smaller than
    the plots, they overflow the output visibly (they aren't clipped).

    The decorated function also gains two read-only attributes: `.value` and
    `.widget`, which are both the rendered `MosaicWidget` instance. Use `.widget`
    to programmatically update the rendered dashboard in place (trait changes on the
    widget are synced to the browser), or to reactively read widget state (e.g., the
    `params` trait, which holds the current selections) with
    :func:`~shinywidgets.reactive_read`.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Note
    ----
    Mosaic runs its queries server-side, in the DuckDB connection the widget holds,
    so which connection that is decides what each Shiny session can see. DataFrames
    passed as ``data=`` are registered in a fresh in-memory connection per widget,
    which keeps sessions isolated. A shared ``con=``, or a ``duckdb`` relation in
    ``data=`` (which mosaic-widget registers on DuckDB's process-wide
    ``duckdb.default_connection()``), is shared by every session: one session's
    registered table replaces another's under the same name, and Mosaic's
    pre-aggregated ``mosaic.preagg_*`` tables are reused across sessions whose
    queries match. Only share a connection for data that is the same for every
    user.

    Each re-render creates a new `MosaicWidget` and DuckDB connection, which
    anywidget currently keeps alive for the life of the server process, and loads
    another copy of the widget's JavaScript into the page. To restyle a dashboard,
    prefer assigning a new spec to ``.widget.spec`` in place (this resets the
    current selections).

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """


class render_obsplot(render_widget_base[ObsplotWidget, ObsplotWidget]):
    """
    Reactively render an [Observable Plot](https://observablehq.com/plot/)
    chart, created with [pyobsplot](https://juba.github.io/pyobsplot/), as a
    Shiny output.

    The decorated function should return a `pyobsplot.widget.ObsplotWidget`
    (requires ``pip install 'shinywidgets[obsplot]'``), as produced by
    `Plot.plot()` (or by calling an `Obsplot()` creator). The `Plot`/`Obsplot`
    object itself is a plot *creator*, not a chart -- calling it with a plot
    specification produces the chart. Only the default ``format='widget'``
    produces a chart; the other formats (``'html'``, ``'svg'``, ``'png'``)
    return `None`, which renders as an empty output.

    Observable Plot charts have a fixed pixel width: they shrink
    proportionally (preserving aspect ratio) to fit a narrower container,
    but never grow past the specification's width. Control the size with
    ``width`` (and, if needed, ``height``) in the plot specification.
    pyobsplot's interactions (tips, crosshairs) run entirely in the browser;
    nothing is synced back to Python, so there's no widget state to
    :func:`~shinywidgets.reactive_read`.

    The decorated function also gains two read-only attributes: `.value` and
    `.widget`, which are both the rendered `ObsplotWidget` instance. To change
    a chart without re-rendering, assign a new specification to
    ``.widget.spec`` (the same dictionary you'd pass to `Plot.plot()`).

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Note
    ----
    pandas and polars `DataFrame`s in the specification are serialized to
    Arrow IPC and sent to the browser with the widget state, so a chart over a
    large dataset makes for a large message (and ``pyobsplot`` bundles about
    1.4 MB of JavaScript, which anywidget sends to the browser again on each
    render). For large data, aggregate before plotting.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Examples
    --------
    ```python
    import polars as pl
    from pyobsplot import Plot
    from shiny.express import ui
    from shinywidgets import render_obsplot

    penguins = pl.read_csv(
        "https://github.com/juba/pyobsplot/raw/main/doc/data/penguins.csv"
    )


    @render_obsplot
    def penguin_plot():
        return Plot.plot(
            {
                "grid": True,
                "color": {"legend": True},
                "marks": [
                    Plot.dot(
                        penguins,
                        {
                            "x": "flipper_length_mm",
                            "y": "body_mass_g",
                            "fill": "species",
                        },
                    )
                ],
            }
        )
    ```
    """


class render_plotnine(render_widget_base[ValueT, MplCanvas]):
    """
    Reactively render a [plotnine](https://plotnine.org) plot as an interactive
    [ipympl](https://matplotlib.org/ipympl/) Shiny output.

    The decorated function may return a `plotnine.ggplot` or a plot composition (e.g.,
    ``p1 | p2``), which is drawn to a matplotlib figure and coerced to an
    `ipympl.backend_nbagg.Canvas` widget (requires ``pip install
    'shinywidgets[plotnine]'``). The returned plot itself isn't modified (a copy is
    drawn). In a filling layout, the
    figure is resized to fit its container (overriding ``theme(figure_size=...)``),
    and plotnine re-lays out the plot (e.g., legends and axis labels) at each size.
    With an explicit ``height``, the figure isn't fitted to the output (it's drawn
    at its ``figure_size``, and a larger figure is clipped), so set
    ``theme(figure_size=...)`` to match. With ``fill=False`` (and no ``height``),
    the figure's width still follows its container.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `Canvas` instance. Use `.widget` to programmatically update the rendered figure
    in place (trait changes on the widget are synced to the browser), or to
    reactively read widget state with :func:`~shinywidgets.reactive_read`.

    Note that plotnine computes axis breaks when it draws, so zooming in (e.g., with
    the toolbar) keeps the original ticks, and a close zoom can show none. For
    zoom-aware ticks, set a matplotlib locator and formatter on the axes of
    `.widget.figure` (e.g., `matplotlib.ticker.MaxNLocator` and `ScalarFormatter`, or
    `matplotlib.dates.AutoDateLocator` for dates) in an effect that reads `.widget`.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """


class render_bokeh(render_widget_base[ValueT, BokehModel]):
    """
    Reactively render a [bokeh](https://bokeh.org) plot as a Shiny output.

    The decorated function may return either a bokeh model (e.g., a
    `bokeh.plotting.figure`), which is coerced to a `jupyter_bokeh.BokehModel`
    widget, or a `jupyter_bokeh.BokehModel` widget (requires ``pip install
    'shinywidgets[bokeh]'``).

    A `figure` fills its output by default (i.e., it gets
    ``sizing_mode="stretch_both"``), unless you give it a ``width``, ``height``,
    ``sizing_mode``, or ``aspect_ratio``, in which case bokeh's own sizing applies.
    Other models (e.g., a `column` or `row` layout) fill only if their
    ``sizing_mode`` stretches vertically (e.g., ``sizing_mode="stretch_both"`` on the
    layout and its children).

    The decorated function also gains two read-only attributes: `.value`, the bokeh
    object most recently returned by the render function, and `.widget`, the rendered
    `BokehModel` instance. To update the plot without re-rendering, modify the
    bokeh models in place (e.g., ``source.data = ...``). Plots that share a
    `ColumnDataSource` (e.g., for linked selection) must be returned together, in
    one layout, from a single render function. Create bokeh models per session
    (e.g., inside the render function), not at the top level of a Shiny Core app,
    where every visitor would share them.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Note
    ---
    **Reacting to user interaction**: bokeh model properties aren't widget
    traits, so :func:`~shinywidgets.reactive_read` can't see them. Instead, the
    output has methods that read what the user does in the plot, much like
    ``input.my_slider()`` reads an input. Call them in a reactive function (a
    ``@render.*`` function, ``@reactive.calc``, or ``@reactive.effect``), which
    then re-runs whenever the interaction changes:

    * ``selected()``: the indices of the selected rows of the plot's
      `ColumnDataSource` (from the tap, box, or lasso select tools), and
      ``selected_rows()``: those rows, as a data frame. These need a plot with
      exactly one `ColumnDataSource`.
    * ``tapped()``: the most recent tap, with its ``.x`` and ``.y`` in data
      units.
    * ``zoomed()``: the plot's ranges after a zoom or pan.

    How they behave:

    * Each returns ``None`` until the interaction happens (``selected_rows()``
      an empty frame). That's a normal state, not an error, so check for it, or
      use ``req(plot.tapped())`` to wait for it.
    * A re-render (e.g. when the render function reads an input) gives the user
      a new plot, so they all start over.
    * Selecting the same points again isn't a change, so readers of
      ``selected()`` don't re-run. Every tap, zoom, or pan re-runs readers of
      ``tapped()`` and ``zoomed()``.
    * ``selected()`` updates at most once the user pauses for 250 ms (see
      ``rate_policy`` and ``rate_delay``).
    * They can't be read inside this output's own render function, which builds
      a new plot each time it runs. To change the plot in response, modify the
      bokeh models from a ``@reactive.effect`` instead.

    For anything else, bokeh's own callbacks (e.g.,
    ``source.selected.on_change("indices", ...)``) work too, and may set
    `reactive.value`s.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    rate_policy
        How to rate-limit :meth:`selected` (debounced by default):
        ``"debounce"`` or ``"throttle"``. ``None`` (the default) keeps the
        debounce.
    rate_delay
        The rate-limit window in seconds (default 0.25). ``0`` disables rate
        limiting.
    """

    _accessor_specs = BOKEH_ACCESSORS

    def selected(self) -> Optional[List[int]]:
        """
        The row indices (into the plot's `ColumnDataSource`) of the most recent
        selection, from a tap, box, or lasso select tool.

        Returns ``None`` until the user selects, and ``[]`` after a selection
        that caught nothing.
        Requires a plot (or layout) with exactly one `ColumnDataSource`.
        Debounced (250 ms) by default; see the ``rate_policy`` and
        ``rate_delay`` parameters.
        """
        return cast(Optional[List[int]], self._read_accessor("selected"))

    def selected_rows(self) -> pd.DataFrame:
        """
        The selected rows (see :meth:`selected`) of the plot's
        `ColumnDataSource`, as a pandas data frame (``source.to_df()``). Empty
        while nothing is selected. Readers also re-run when ``source.data``
        changes.
        """
        indices = self.selected()
        self._read_accessor("source_data")
        return selected_frame(cast("BokehModel", self._widget), indices)

    def tapped(self) -> Optional[Tap]:
        """
        The most recent tap on a plot, as a `bokeh.events.Tap` (``.x`` and
        ``.y`` in data units, ``.model`` the plot). Returns ``None`` until the
        user taps. Not rate-limited.
        """
        return cast(Optional["Tap"], self._read_accessor("tapped"))

    def zoomed(self) -> Optional[RangesUpdate]:
        """
        The plot ranges after the most recent zoom or pan, as a
        `bokeh.events.RangesUpdate` (``.x0``, ``.x1``, ``.y0``, ``.y1``,
        ``.model``). Returns ``None`` until the user zooms or pans. Not
        rate-limited (bokeh reports once per gesture).
        """
        return cast(Optional["RangesUpdate"], self._read_accessor("zoomed"))

    def auto_output_ui(self) -> Tag:
        res = super().auto_output_ui()
        res.children.append(_bokeh_dependency())
        return res


class render_panel(render_widget_base[ValueT, BokehModel]):
    """
    Reactively render a [panel](https://panel.holoviz.org) object as a Shiny output.

    The decorated function may return any object that ``pn.panel()`` accepts (e.g., a
    pane, widget, layout, `pn.viewable.Viewer`, string, DataFrame, or figure), which
    is rendered through bokeh (requires ``pip install 'shinywidgets[panel]'``), or the
    underlying `jupyter_bokeh.BokehModel` widget. Panel callbacks (e.g., ``pn.bind()``,
    ``.param.watch()``, and ``on_click()``) run in the Shiny server, without a Panel
    server.

    The decorated function also gains two read-only attributes: `.value`, the object
    most recently returned by the render function, and `.widget`, the rendered
    `BokehModel` instance. `.value` is the return value exactly as returned -- to get
    a Panel object with a parameter interface, return a pane or widget explicitly
    rather than a raw value like a DataFrame. To update the output without
    re-rendering, modify `.value` in place (e.g., ``table.value.value = df``).
    Panel parameters are not
    widget traits, so instead of :func:`~shinywidgets.reactive_read`, use
    ``.param.watch()`` to react to them (e.g., ``slider.param.watch(lambda e:
    val.set(e.new), "value")``, where ``val`` is a `reactive.value`).

    Some other things to know:

    * Set ``sizing_mode="stretch_both"`` on the panel object to fill the output.
    * Call ``pn.extension()`` with the extensions you use (e.g.,
      ``pn.extension("tabulator")``) at the top of the app, especially for
      components that may first appear after the initial render (e.g., inside
      ``pn.bind()``). Otherwise they render blank.
    * Create panel objects per session (e.g., inside the render function), not at the
      top level of a Shiny Core app, where every visitor would share them (and see
      each other's changes).
    * Panel templates are full pages, so they can't be rendered in an output; use
      Shiny's page layouts instead.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    def auto_output_ui(self) -> Tag:
        res = super().auto_output_ui()
        res.children.append(_bokeh_dependency())
        return res

    def _as_widget(self, value: ValueT) -> BokehModel:
        if isinstance(value, Widget):
            return super()._as_widget(value)
        # Like Panel itself, render anything pn.panel() accepts (e.g., a string or
        # DataFrame), and render figures as Panel panes rather than through
        # their own package's widget (e.g., a plotly FigureWidget)
        return cast(BokehModel, as_widget_panel(value))


class render_holoviews(render_widget_base[ValueT, BokehModel]):
    """
    Reactively render a [holoviews](https://holoviews.org),
    [hvPlot](https://hvplot.holoviz.org), or [geoviews](https://geoviews.org) object
    as a Shiny output.

    The decorated function may return either a holoviews/hvplot/geoviews object
    (which is rendered through panel; requires ``pip install 'shinywidgets[holoviews]'``)
    or the underlying `jupyter_bokeh.BokehModel` widget. geoviews 1.15 requires
    ``cartopy<0.26``. If you call ``.opts()`` without importing hvplot, call
    ``hv.extension("bokeh")`` first. Plots rasterized with
    [datashader](https://datashader.org) are supported too (e.g., hvPlot's
    ``rasterize=True`` or holoviews' ``rasterize()`` operation; requires
    ``pip install datashader``): they re-aggregate the data on the server for the
    visible region whenever the user zooms or pans. Build such plots inside the
    render function rather than once at module level: holoviews links every
    display of the same object, so a shared plot would apply one user's zoom to
    every session's plot. Also note that re-aggregation runs on the server's
    event loop, so a slow aggregation delays every session served by that
    process.

    Linked streams (e.g., ``holoviews.streams.Tap`` or ``BoundsXY``) run their
    callbacks outside Shiny's reactive cycle: with shiny < 1.9, the updates they
    trigger only reach the browser after the next unrelated input. And because
    ``.opts()`` styles shared objects such as ``gv.tile_sources.OSM`` or
    ``gv.feature.coastline`` in place, use ``.opts(..., clone=True)`` on them, or
    one session's styling will show up in every session.

    HoloViews and hvPlot plots have a fixed size by default (and get clipped by a
    smaller container). To make a plot fill its output, pass ``responsive=True``
    (e.g., ``df.hvplot.line(..., responsive=True)`` or ``.opts(responsive=True)``),
    optionally with a fixed ``height``. If you give the output a fixed height, set
    ``fillable=True`` too (e.g., ``output_widget("map", height="400px",
    fillable=True)``); otherwise a responsive plot collapses to a thin strip.

    The decorated function also gains two read-only attributes: `.value`, the
    holoviews/hvplot object most recently returned by the render function, and
    `.widget`, the rendered `BokehModel` instance. HoloViews' own Python-side
    interactivity (e.g., widgets for a ``HoloMap`` or ``DynamicMap``, streams such as
    ``Selection1D`` or ``BoundsXY``, and ``hv.link_selections``) works without a Bokeh
    server. To react to it in Shiny, set a `reactive.value` from a stream subscriber
    or a ``.param.watch()`` callback (e.g., ``links.param.watch(lambda e:
    selection.set(e.new), "selection_expr")``) instead of using
    :func:`~shinywidgets.reactive_read`. To update a plot without re-rendering, drive
    a ``DynamicMap`` with a stream (e.g., call ``stream.event(...)`` or
    ``pipe.send(...)`` in a `reactive.effect`).

    Create streams and ``link_selections`` instances per session (e.g., in the
    server function, or anywhere in a Shiny Express app), not at the top level of a
    Shiny Core app, where every visitor would share them (and see each other's
    selections).

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    def auto_output_ui(self) -> Tag:
        res = super().auto_output_ui()
        res.children.append(_bokeh_dependency())
        return res


class render_perspective(render_widget_base[ValueT, PerspectiveWidget]):
    """
    Reactively render a [perspective](https://perspective-dev.github.io) viewer as a
    Shiny output.

    The decorated function may return a `pandas` or `polars` DataFrame or a
    `perspective.Table` (both are coerced to a `perspective.widget.PerspectiveWidget`;
    requires ``pip install 'shinywidgets[perspective]'``), or a
    `perspective.widget.PerspectiveWidget` widget. A pandas index becomes an ``index``
    column.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `PerspectiveWidget` instance. Use `.widget` to programmatically update the rendered
    viewer in place (e.g., `.widget.update()` streams new rows, and trait changes are
    synced to the browser), or to reactively read widget state (e.g., `plugin`,
    `group_by`, `sort`, or `filter`) with :func:`~shinywidgets.reactive_read`.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Note
    ---
    Perspective keeps every table it hosts in memory for the life of the process, so a
    table created from a DataFrame is not freed when the output re-renders. To change
    the data, prefer updating the existing viewer in place: `.widget.update(df)`
    appends rows (or upserts them, for a table with an ``index``), and
    `.widget.clear()` followed by `.widget.update(df)` swaps them out.
    (`.widget.replace()` also swaps rows, but as of perspective-python 5.6 it only
    accepts records, a dict of columns, or Arrow IPC bytes, not a DataFrame.)

    A viewer's browser can list, read, and write every table on its widget's
    Perspective server. A DataFrame gets a server of its own, so other sessions
    can't reach its data. Tables made with ``perspective.table()`` (and widgets made
    with ``PerspectiveWidget(df)``) live on Perspective's process-wide server,
    which every session's viewer can reach, so only use them for data that every
    user may see and edit. For per-user data, create the table on a private server
    instead: ``perspective.Server().new_local_client().table(df)``.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    def _as_widget(self, value: ValueT) -> PerspectiveWidget:
        # DataFrames are generic types that other renderers accept too, so
        # they can't be registered in AS_WIDGET_MAP. Checked by name (pandas and
        # polars are optional) and through the MRO, so subclasses (e.g.,
        # geopandas.GeoDataFrame, or an app-defined subclass) count too.
        if any(
            widget_pkg(cls) in ("pandas", "polars") and cls.__name__ == "DataFrame"
            for cls in type(value).__mro__
        ):
            return perspective_widget(value)
        return super()._as_widget(value)


class render_ipydatagrid(render_widget_base[ValueT, DataGrid]):
    """
    Reactively render a pandas DataFrame as an interactive
    [ipydatagrid](https://github.com/bloomberg/ipydatagrid) data grid Shiny output.

    The decorated function may return either a `pandas.DataFrame` (which is coerced to
    an `ipydatagrid.DataGrid`; requires ``pip install 'shinywidgets[ipydatagrid]'``) or an
    `ipydatagrid.DataGrid` widget. Pass a `DataGrid` to customize the grid (e.g.,
    `selection_mode`, `editable`, or cell renderers).

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `DataGrid` instance. Use `.widget` to programmatically update the rendered grid
    in place (trait changes on the widget are synced to the browser), or to
    reactively read widget state (e.g., `selections`) with
    :func:`~shinywidgets.reactive_read`.

    Some ipydatagrid behaviors worth knowing about:

    * A returned DataFrame uses ipydatagrid's default ``selection_mode="none"``, so
      `selections` stays empty; return ``DataGrid(df, selection_mode="row")`` (or
      ``"cell"``/``"column"``) to let users select.
    * `selections` index the grid as displayed (after any sort or filter), so map
      them through ``.widget.get_visible_data()``.
    * ``DataGrid.select()``, ``DataGrid.clear_selection()`` and cell edits modify the
      widget's state in place, which doesn't trigger
      :func:`~shinywidgets.reactive_read`. Assign a new list to ``.widget.selections``
      instead, and use ``.widget.on_cell_change()`` to react to edits.
    * Cell renderers and scales are widgets too, so create them inside the render
      function rather than at import time.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    # A DataFrame is a generic type (several renderers accept one), so it isn't
    # registered with as_widget()
    def _as_widget(self, value: ValueT) -> DataGrid:
        if is_pandas_dataframe(value):
            return dataframe_to_datagrid(cast("pd.DataFrame", value))
        return super()._as_widget(value)


def is_pandas_dataframe(value: object) -> bool:
    # Checked by name (pandas is optional) and through the MRO, so subclasses such
    # as geopandas.GeoDataFrame count
    return any(
        widget_pkg(cls) == "pandas" and cls.__name__ == "DataFrame"
        for cls in type(value).__mro__
    )


def dataframe_to_datagrid(df: pd.DataFrame) -> DataGrid:
    try:
        from ipydatagrid import DataGrid
    except ImportError:
        raise ImportError(
            "Install the ipydatagrid package to use render_ipydatagrid with "
            "shinywidgets (pip install 'shinywidgets[ipydatagrid]')."
        )
    return DataGrid(df)


class render_ipyfilechooser(render_widget_base[ValueT, FileChooser]):
    """
    Reactively render an [ipyfilechooser](https://github.com/crahan/ipyfilechooser)
    file chooser as a Shiny output.

    The decorated function should return an `ipyfilechooser.FileChooser` widget
    (requires ``pip install 'shinywidgets[ipyfilechooser]'``). The chooser is a
    form control with a natural size, so the output doesn't fill its container;
    size it with the chooser's own ``layout`` (e.g., ``layout=Layout(width='700px')``)
    or with ``output_widget(width=..., height=...)``.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `FileChooser` instance. Note that the chooser's ``selected``,
    ``selected_path`` and ``selected_filename`` are plain Python properties (not
    widget traits), so they can't be read with
    :func:`~shinywidgets.reactive_read`. To react to a selection, pass
    ``.widget.register_callback()`` a function that sets a `reactive.value` (the
    callback fires when the user confirms or changes a selection).

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Examples
    --------
    ```python
    from ipyfilechooser import FileChooser
    from shiny import App, reactive, render, ui
    from shinywidgets import output_widget, render_ipyfilechooser

    app_ui = ui.page_fluid(
        output_widget("chooser"),
        ui.output_text("selected"),
    )


    def server(input, output, session):
        selection = reactive.value(None)

        @render_ipyfilechooser
        def chooser():
            fc = FileChooser()
            fc.register_callback(lambda fc: selection.set(fc.selected))
            return fc

        @render.text
        def selected():
            return f"Selected: {selection()}"


    app = App(app_ui, server)
    ```
    """


class render_plotly(render_widget_base[PlotlyValueT, FigureWidget]):
    """
    Reactively render a [plotly](https://plotly.com/python/) figure as a Shiny output.

    The decorated function may return either a `plotly.graph_objects.Figure` (which
    is coerced to a `FigureWidget`) or a `plotly.graph_objects.FigureWidget` widget
    (requires ``pip install 'shinywidgets[plotly]'``).
    Alternatively, it may return a Dash-style
    `(figure, config)` tuple, where `config` is a dict of Plotly.js [config
    options](https://plotly.com/javascript/configuration-options/) (e.g.,
    `{"displayModeBar": False}`), mirroring Dash's `dcc.Graph(figure=..., config=...)`
    API. The config is merged over plotly's defaults, so it also takes precedence over
    shinywidgets' own defaults (e.g., `responsive`).

    The decorated function also gains two read-only attributes: `.value`, which is
    exactly what the render function returned (a figure or the `(figure, config)`
    tuple), and `.widget`, which is always the coerced `FigureWidget` (with `config`
    merged into its ``_config`` trait). Use `.widget` to programmatically update the
    rendered figure in place (trait changes on the widget are synced to the browser).
    When the render function returns a `go.Figure`, `.value` is that figure, not the
    displayed one, so modifying it has no effect.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Note
    ---
    **Reacting to user interaction**: the output has methods that read what the
    user does in the plot, much like ``input.my_slider()`` reads an input. Call
    them in a reactive function (a ``@render.*`` function, ``@reactive.calc``, or
    ``@reactive.effect``), which then re-runs whenever the interaction changes:

    * ``clicked()``: the clicked points.
    * ``selected()``: the points of a box or lasso selection, once the drag ends
      (``selecting()``: the same, while the user drags).
    * ``brushed()``: the selected region itself (``brushing()``: while dragging).
    * ``relayout()``: the axis ranges after a zoom, pan, or autoscale.
    * ``selected_rows(df)``: the rows of your data the user selected. This needs
      each point to carry its row as ``customdata``, e.g.
      ``px.scatter(df, ..., custom_data=[df.index])``; see the method for
      details.

    How they behave:

    * Each returns ``None`` until the interaction happens. That's a normal
      state, not an error, so check for it (``req(pts is not None)``; not
      ``req(pts)``, since a data frame has no truth value).
    * A re-render (e.g. when the render function reads an input) gives the user
      a new plot, so they all start over at ``None``.
    * Repeating an interaction (clicking the same point twice) isn't a change,
      so readers don't re-run.
    * As in the plot itself, a double-click clears ``clicked()``, and a deselect
      (double-clicking after a selection) clears the selection accessors.
    * The streaming ones, ``selecting()`` and ``brushing()``, update at most
      once the user pauses for 250 ms (see ``rate_policy`` and ``rate_delay``).
    * They can't be read inside this output's own render function, which builds
      a new plot each time it runs. To change the plot in response to a click,
      modify ``.widget`` from a ``@reactive.effect`` instead (see the example).

    **Updating in place**: re-rendering rebuilds the figure, resetting zoom and
    selection. To change a displayed figure instead, read inputs under
    `reactive.isolate()` in the render function and modify `.widget` in a
    `reactive.effect` (use ``with .widget.batch_update():`` for many changes, or
    ``.widget.batch_animate()`` for animated transitions).

    **Sizing**: a figure with an explicit ``layout.height`` keeps that height
    instead of filling its container. For a plot that fills a fixed height, use
    ``output_widget("id", height="450px", fillable=True)``: without
    ``fillable=True``, the plot renders at plotly's default height (360px)
    regardless of the output's height.

    **Typing**: no return-type annotation is needed -- the renderer's value
    type is statically bounded, so type checkers flag unsupported return
    values at decoration time, and the output's `.value` attribute is
    inferred from the render function's actual return type. If you do
    annotate, annotate narrowly (e.g., ``-> go.Figure`` or ``-> tuple[go.Figure,
    dict[str, Any]]``): `.value` is typed from the annotation, so annotating
    with a wide union of all supported shapes would force you to narrow
    `.value` before each use.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    rate_policy
        How to rate-limit :meth:`selecting` and :meth:`brushing` (debounced by
        default) and :func:`~shinywidgets.reactive_read` on the widget:
        ``"debounce"`` or ``"throttle"``. ``None`` (the default) keeps each
        accessor's own default, and debounces ``reactive_read()`` only if
        ``rate_delay`` is given.
    rate_delay
        The rate-limit window in seconds (default 0.25). ``0`` disables rate
        limiting.

    Examples
    --------
    ```python
    from shiny import App, ui
    from shinywidgets import output_widget, render_plotly
    import plotly.graph_objects as go

    app_ui = ui.page_fluid(output_widget("plot"))


    def server(input, output, session):
        @render_plotly
        def plot():
            fig = go.Figure(go.Scatter(x=[1, 2, 3], y=[1, 4, 9]))
            return fig, {"displayModeBar": False}


    app = App(app_ui, server)
    ```

    Reacting to clicks and selections:

    ```python
    import plotly.express as px
    from shiny import reactive, req
    from shiny.express import render
    from shinywidgets import render_plotly

    df = px.data.iris()


    @render_plotly
    def plot():
        fig = px.scatter(df, x="sepal_width", y="sepal_length", custom_data=[df.index])
        return fig.update_layout(dragmode="select")


    @render.data_frame
    def picked():
        return plot.selected_rows(df)  # empty until the user selects


    @reactive.effect
    def _():
        pts = plot.clicked()
        req(pts is not None)
        plot.widget.layout.title.text = f"Clicked x={pts['x'].iloc[0]}"
    ```
    """

    _accessor_specs = PLOTLY_ACCESSORS

    def clicked(self) -> Optional[pd.DataFrame]:
        """
        The points of the most recent click, one row per point.

        Columns are ``trace_index``, ``point_index`` (the point's position
        within its trace, not a row of your data), ``x``, ``y``, and ``z`` and
        ``customdata`` when the figure has them. Returns ``None`` until the user
        clicks, and again after a double-click or deselect, so check for
        ``None`` (e.g. ``req(pts is not None)``) to wait for a click. Clicking
        the same point twice doesn't fire twice. Not rate-limited. Requires
        pandas.
        """
        return cast(Optional["pd.DataFrame"], self._read_accessor("clicked"))

    def selected(self) -> Optional[pd.DataFrame]:
        """
        The points of the most recent box or lasso selection, once the gesture
        ends, with the same columns as :meth:`clicked`.

        Returns ``None`` until the user selects, and again after a deselect
        (double-click); an empty frame for a selection that caught no points.
        Not rate-limited. Requires pandas. See :meth:`selected_rows` for rows of
        your data.
        """
        return cast(Optional["pd.DataFrame"], self._read_accessor("selected"))

    def selecting(self) -> Optional[pd.DataFrame]:
        """
        Like :meth:`selected`, but updates while the user drags the selection.
        Debounced (250 ms) by default; see the ``rate_policy`` and
        ``rate_delay`` parameters.
        """
        return cast(Optional["pd.DataFrame"], self._read_accessor("selecting"))

    def brushed(self) -> Optional[Dict[str, Any]]:
        """
        The region of the most recent selection, once the gesture ends:
        ``{"range": {"x": [x0, x1], "y": [y0, y1]}}`` for a box, or
        ``{"lassoPoints": {"x": [...], "y": [...]}}`` for a lasso, in data
        coordinates (as plotly.js reports them).

        Returns ``None`` until the user selects, and again after a deselect.
        Not rate-limited.
        """
        return cast(Optional[Dict[str, Any]], self._read_accessor("brushed"))

    def brushing(self) -> Optional[Dict[str, Any]]:
        """
        Like :meth:`brushed`, but updates while the user drags the selection.
        Debounced (250 ms) by default; see the ``rate_policy`` and
        ``rate_delay`` parameters.
        """
        return cast(Optional[Dict[str, Any]], self._read_accessor("brushing"))

    def relayout(self) -> Optional[Dict[str, Any]]:
        """
        The axis changes of the most recent zoom, pan, or autoscale, as
        plotly.js reports them: keys like ``"xaxis.range[0]"`` and
        ``"xaxis.autorange"`` (other relayout keys are dropped).

        Returns ``None`` until the user changes an axis. Not rate-limited
        (plotly.js reports once per gesture).
        """
        return cast(Optional[Dict[str, Any]], self._read_accessor("relayout"))

    def selected_rows(
        self, df: IntoDataFrameT, *, key: Optional[str] = None
    ) -> IntoDataFrameT:
        """
        The rows of `df` that the user selected (see :meth:`selected`).

        Plotly reports points of the plot, not rows of your data, so each point
        must carry its row's identity as ``customdata``, which is matched to
        `df`:

        * pandas: ``px.scatter(df, ..., custom_data=[df.index])``. Matched to
          `df`'s index labels, so this also works on a filtered or sorted `df`.
        * Any frame (e.g., polars), by a key column: ``custom_data=["id"]``
          with ``key="id"``. Matched to that column's values. Without an id
          column, add one with ``df.with_row_index("id")``.

        Returns an empty frame while nothing is selected, so it can be passed
        straight to ``@render.data_frame``.
        """
        points = self._read_accessor("selected", raw=True)
        return select_rows(cast(Optional[List[Point]], points), df, key)

    def _as_widget(self, value: PlotlyValueT) -> FigureWidget:
        fig, config = _split_config(value)
        widget = super()._as_widget(cast(PlotlyValueT, fig))
        if config:
            widget._config = {**widget._config, **config}  # type: ignore
        return widget


def _split_config(value: object) -> tuple[object, Optional[Dict[str, Any]]]:
    # Dash-style (figure, config) tuple. Any non-tuple value is passed through to
    # as_widget(), which raises a helpful error if it can't be coerced.
    if not isinstance(value, tuple):
        return value, None
    if len(value) == 2 and isinstance(value[1], dict):
        return value[0], value[1]
    # A tuple that isn't (figure, config) would just fail coercion in as_widget()
    # anyway, so fail here with a more actionable message instead.
    problem = f"a tuple of length {len(value)}"
    if len(value) >= 2 and not isinstance(value[1], dict):
        problem += f" whose second element is {type(value[1]).__name__}, not a dict"
    raise TypeError(
        "A @render_plotly render function may return a (figure, config) tuple, where "
        "config is a dict of Plotly.js config options (e.g., {'displayModeBar': False}), "
        f"but got {problem}."
    )


class render_pythreejs(render_widget_base[ValueT, PythreejsRenderer]):
    """
    Reactively render a [pythreejs](https://pythreejs.readthedocs.io) 3D scene as a
    Shiny output.

    The decorated function should return a `pythreejs.Renderer` widget (i.e., a
    `Scene` plus a camera, with meshes/lights added to the scene; requires ``pip
    install 'shinywidgets[pythreejs]'``). By default, the scene fills its container (the canvas and
    camera aspect resize with it); give the `Renderer` an explicit ``width`` or
    ``height`` (or a `layout` height) to use a fixed pixel size instead.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `Renderer` instance. Use `.widget` to programmatically update the rendered scene
    in place (trait changes on the widget are synced to the browser), or to
    reactively read widget state with :func:`~shinywidgets.reactive_read`. With
    `pythreejs.OrbitControls` (or `TrackballControls`), the camera's ``position``,
    ``quaternion``, and ``zoom`` sync back to Python each time the user finishes
    orbiting, so e.g. ``reactive_read(scene.widget.camera, "position")`` picks up
    every interaction.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Notes
    -----
    * Scene background: set `pythreejs.Scene(background=...)` (it defaults to
      white and overrides ``Renderer(background=...)``).
    * Give `pythreejs.DirectionalLight`/`pythreejs.SpotLight` an explicit
      ``target`` (added to the scene) and ``shadow`` (with a camera) --
      pythreejs creates defaults for them in the browser otherwise, and
      browser-created widgets live until the session ends, so every re-render
      would leak 3 models per light (and log a transient console error).
    * Rotate objects via ``mesh.quaternion``; pythreejs's ``rotation`` (Euler)
      updates don't render (an upstream pythreejs bug).
    """


class render_pydeck(render_widget_base[ValueT, DeckGLWidget]):
    """
    Deprecated: use pydeck layers with :class:`~shinywidgets.render_maplibre`
    instead.

    pydeck v0.9 removed its Jupyter widget (`Deck.show()` now returns static HTML and
    `Deck.update()` raises), so no ipywidgets bridge, shinywidgets included, can
    render a live `pydeck.Deck`. With pydeck v0.9 or newer, this decorator raises a
    `TypeError` explaining the alternatives below. (pydeck v0.8's widget requires
    ipywidgets < 8, while shinywidgets requires ipywidgets >= 8.1.)

    Alternatives:

    * **Reactive maps from pydeck layers:** pass `pydeck.Layer` objects to a
      [maplibre](https://eoda-dev.github.io/py-maplibregl/) map's
      `add_deck_layers()` and render it with
      :class:`~shinywidgets.render_maplibre` (requires ``pip install
      'shinywidgets[maplibre]'``). Restyle the rendered map in place with
      `.widget.set_deck_layers()` (the camera stays where the user left it), and
      read its state (e.g., ``"view_state"``, ``"clicked"``) with
      :func:`~shinywidgets.reactive_read`.
    * **Large data:** [lonboard](https://developmentseed.org/lonboard/) and
      :class:`~shinywidgets.render_lonboard` send binary data once and restyle
      layers without re-sending it.
    * **Static maps:** use shiny's ``@render.ui`` and return ``deck.show()`` (a
      500px-tall iframe), or, to fill the container,
      ``ui.tags.iframe(srcdoc=deck.to_html(as_string=True),
      style="border:0;width:100%;height:100%;flex:1 1 auto")``. Every change
      re-sends the whole page and resets the camera, and there are no events back to
      Python. (Don't return ``deck.to_html()``: without a filename, it returns
      ``None``.)

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Examples
    --------
    ```python
    import pydeck as pdk
    from maplibre import Map, MapOptions
    from maplibre.basemaps import Carto
    from shiny import reactive
    from shiny.express import input, ui
    from shinywidgets import render_maplibre

    ui.input_slider("radius", "Hexagon radius (m)", 1000, 10000, 4000, step=500)

    POINTS = [[-0.13, 51.51], [-0.12, 51.50], [-2.24, 53.48]]  # [lng, lat]


    @render_maplibre
    def deck():
        m = Map(MapOptions(style=Carto.DARK_MATTER, center=(-1.9, 52.25), zoom=6))
        # Filled (and restyled in place, without re-rendering the map) below
        m.add_deck_layers([])
        return m


    @reactive.effect
    def _():
        deck.widget.set_deck_layers([layer()])


    def layer():
        return pdk.Layer(
            "HexagonLayer",
            POINTS,
            id="hex",
            get_position="-",
            radius=input.radius(),
            extruded=True,
        )
    ```
    """

    def __init__(
        self,
        _fn: Optional[ValueFn[ValueT]] = None,
        *,
        width: Optional[str] = None,
        height: Optional[str] = None,
        fill: Optional[bool] = None,
        fillable: Optional[bool] = None,
        rate_policy: Optional[RatePolicy] = None,
        rate_delay: Optional[float] = None,
    ):
        warnings.warn(
            "render_pydeck is deprecated: pydeck v0.9 removed its Jupyter widget, so "
            "it can't render maps. Pass pydeck.Layer objects to a maplibre Map's "
            "add_deck_layers() and use @render_maplibre instead (see "
            "help(shinywidgets.render_pydeck) for other alternatives).",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            _fn,
            width=width,
            height=height,
            fill=fill,
            fillable=fillable,
            rate_policy=rate_policy,
            rate_delay=rate_delay,
        )

    def _as_widget(self, value: ValueT) -> DeckGLWidget:
        # A DeckGLWidget (which as_widget() passes through) can't render either
        if not pydeck_has_widget():
            raise TypeError(PYDECK_NO_WIDGET_MESSAGE)
        return super()._as_widget(value)


class render_pygwalker(render_widget_base[ValueT, WalkerWidget]):
    """
    Reactively render a [PyGWalker](https://docs.kanaries.net/pygwalker) data
    exploration app as a Shiny output.

    The decorated function may return either a pandas `DataFrame` (which is coerced to
    a PyGWalker widget; requires ``pip install 'shinywidgets[pygwalker]'``) or a widget created by
    `pygwalker.api.anywidget.walk()` (use this to pass options like ``theme_key``).
    A polars `DataFrame` is coerced too, but only when the installed pygwalker can read
    it: every release so far trips over dtype groups that polars 1.0 removed (the fix
    is merged upstream and due in pygwalker 0.6), so it's rejected with a hint to
    convert it (``df.to_pandas()``).
    Don't use the top-level `pygwalker.walk()`: outside of Jupyter, it starts a
    blocking web server instead of returning a widget.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    PyGWalker widget. The widget has no traits that track the explorer's state, so
    there's nothing to :func:`~shinywidgets.reactive_read`, and changing the explorer
    means re-rendering it. Each render sends PyGWalker's JavaScript (about 10 MB) to
    the browser, so avoid unnecessary re-renders.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output. Outside of
    filling layouts, give it a height (e.g., ``"800px"``) that fits PyGWalker's UI.

    Note
    ----
    **Privacy**: by default, PyGWalker sends usage events and checks for updates,
    from both the Python process and each visitor's browser. Call
    ``pygwalker.GlobalVarManager.set_privacy("offline")`` (before rendering) to
    disable both.

    **Security**: PyGWalker computes charts by running SQL that the browser sends on
    DuckDB's process-wide default connection, and any visitor can send arbitrary SQL,
    including SQL that reads or writes files on the server. So, this renderer
    *requires* that connection to be locked down before it renders anything; if it
    isn't, rendering raises an error. Do this when the app starts (this also applies
    to any other code in the process that uses ``duckdb.sql()`` and friends without a
    connection):

    ```python
    import duckdb

    # Set first: PyGWalker sets it per query, which a locked configuration refuses
    duckdb.execute("SET TimeZone = 'UTC'")
    duckdb.execute("SET enable_external_access = false")
    duckdb.execute("SET lock_configuration = true")
    ```

    ``lock_configuration`` is permanent for the connection, so set anything else you
    need first (e.g., ``SET memory_limit = '2GB'``). shinywidgets also restricts the
    SQL the browser can send to single ``SELECT`` statements against the widget's own
    data (no DDL and no other tables or views, which the connection shared with every
    other PyGWalker widget in the process would otherwise expose to every visitor),
    and rejects the browser actions that can't be made safe: ``upload_spec_to_cloud``
    with a visitor-supplied Kanaries token (it would overwrite the server's stored
    credentials) and ``open_in_desktop`` (it launches the server's ``gw://`` handler).

    Even then, the explorer is best suited to trusted users. Every PyGWalker widget
    in the process shares the one connection and one table name
    (``pygwalker_mid_table``), so per-user data is kept apart only by each request
    re-registering its own data right before it queries -- which holds while Shiny
    handles requests on a single thread, but is not a boundary you can build on. And
    a visitor can still send expensive queries, which block the Python process (every
    session, not just theirs) while they run. If different users must explore
    different, mutually private datasets, prefer a renderer that keeps data apart by
    design.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    # DataFrames are generic (several renderers accept them), so they can't be
    # registered in AS_WIDGET_MAP
    def _as_widget(self, value: ValueT) -> WalkerWidget:
        if is_dataframe(value, "polars") and not polars_supported():
            raise TypeError(
                "PyGWalker can't read polars DataFrames with polars >= 1.0 (its polars "
                "parser still uses dtype groups that polars removed; the fix is merged "
                "upstream and due in pygwalker 0.6, but no release has it yet "
                "-- https://github.com/Kanaries/pygwalker/commit/5055d702). Pass a "
                "pandas DataFrame instead (e.g., df.to_pandas())."
            )
        if not (is_dataframe(value, "pandas") or is_dataframe(value, "polars")):
            widget = super()._as_widget(value)
            # A widget from walk() is PyGWalker's too, and needs the same lockdown and
            # the same rejected actions as one this renderer creates
            if is_walker_widget(widget):
                require_duckdb_lockdown()
                harden_walker_widget(widget)
            return widget

        try:
            from pygwalker.api.anywidget import walk  # pyright: ignore[reportMissingImports]
        except ImportError:
            raise ImportError(
                "Install the pygwalker package to use render_pygwalker with shinywidgets (pip install 'shinywidgets[pygwalker]')."
            )

        require_duckdb_lockdown()
        return harden_walker_widget(walk(value))


# PyGWalker hands the browser a set of request handlers (see PygWalker._init_callback).
# Two of them let a visitor reach outside the app: `upload_spec_to_cloud` accepts a
# Kanaries token from the browser (which pygwalker writes to its config file and to
# process-wide state), so harden_walker_widget makes it refuse one; `open_in_desktop`
# has no safe form at all (it shells out to the server's `gw://` protocol handler with
# the whole data source in the URL), so it's rejected outright.
_WALKER_BLOCKED_ACTIONS = ("open_in_desktop",)

# Three more handlers run SQL verbatim from the browser (`get_datas` takes "sql",
# batch_get_datas_by_sql a "queryList", export_dataframe_by_sql a "sql") on DuckDB's
# default connection, which every PyGWalker widget in the process shares (under one
# fixed view name, pygwalker_mid_table). harden_walker_widget wraps them so a visitor
# can only read their own widget's data: no DDL (a CREATE TABLE would persist in the
# shared database for every visitor to see), no other statements, and no tables or
# views other than the widget's own. Per-widget connections upstream would make this
# unnecessary (https://github.com/Kanaries/pygwalker/issues/747).
_WALKER_SQL_ACTIONS = (
    "get_datas",
    "batch_get_datas_by_sql",
    "export_dataframe_by_sql",
)

_WALKER_TABLE_NAME = "pygwalker_mid_table"

_DUCKDB_UNLOCKED_MESSAGE = """\
Can't render a PyGWalker explorer: DuckDB's default connection isn't locked down.

PyGWalker computes charts by running the SQL its browser sends on that connection, and
any visitor can send arbitrary SQL -- including SQL that reads or writes files on the
server. Lock the connection down when the app starts:

    import duckdb

    # Set first: PyGWalker sets it per query, which a locked configuration refuses
    duckdb.execute("SET TimeZone = 'UTC'")
    duckdb.execute("SET enable_external_access = false")
    duckdb.execute("SET lock_configuration = true")

lock_configuration can't be undone, so set anything else you need (e.g.
SET memory_limit = '2GB') before it."""


# The browser picks both the name and the value of this setting, and pygwalker writes
# the token to its config file and to process-wide state (GlobalVarManager), so it
# must come from the app, not from a visitor.
_WALKER_TOKEN_MESSAGE = """\
shinywidgets rejected PyGWalker's upload_spec_to_cloud because the request supplied a
Kanaries token. Visitors can't set the server's credentials: pass kanaries_api_key to
pygwalker.api.anywidget.walk() (or set it in the environment) instead."""


_WALKER_SQL_MESSAGE = """\
shinywidgets rejected a SQL query from PyGWalker's browser because it isn't a single
SELECT against the widget's own data. PyGWalker runs the SQL its browser sends on
DuckDB's default connection, which every PyGWalker widget in the process shares, so
visitors may only read their own widget's data (no DDL and no other tables or views)."""


def is_walker_widget(x: object) -> bool:
    # The widget class is pygwalker.api.anywidget._WalkerWidget in pygwalker <= 0.5
    # and pygwalker.services.anywidget_widget.WalkerAnyWidget in 0.6+
    return any(
        widget_pkg(cls) == "pygwalker"
        and cls.__name__ in ("_WalkerWidget", "WalkerAnyWidget")
        for cls in type(x).__mro__
    )


def polars_supported() -> bool:
    """
    Whether pygwalker can read polars data with the installed polars (and pygwalker).

    Every pygwalker release so far builds its field specs from dtype groups that polars
    1.0 removed (``pl.NUMERIC_DTYPES`` and friends). Upstream replaced them with
    ``dtype.is_numeric()`` and friends (Kanaries/pygwalker@5055d702, merged in PR #734
    and staged for 0.6 -- main is at 0.6.0rc0 -- but unpublished), so look for it
    (``_is_numeric_dtype``) as well as for polars old enough to still have the groups.
    Unknown answers are treated as supported: this is a hint for a broken combination,
    not a guarantee.
    """
    import polars as pl

    if hasattr(pl, "NUMERIC_DTYPES"):
        return True
    try:
        from pygwalker.data_parsers import polars_parser  # pyright: ignore[reportMissingImports]
    except ImportError:
        return True
    return hasattr(polars_parser, "_is_numeric_dtype")


def require_duckdb_lockdown() -> None:
    """Raise unless DuckDB's default connection can't reach outside of DuckDB."""
    external_access, locked = duckdb_settings()
    if external_access or not locked:
        raise RuntimeError(_DUCKDB_UNLOCKED_MESSAGE)


def walker_comm(widget: Widget) -> Optional[Any]:
    """PyGWalker's comm for `widget`, which holds its request handlers."""
    callbacks = getattr(getattr(widget, "_msg_callbacks", None), "callbacks", ())
    for callback in callbacks:
        owner = getattr(callback, "__self__", None)
        if isinstance(getattr(owner, "_endpoint_map", None), dict) and callable(
            getattr(owner, "register", None)
        ):
            return owner
    return None


def harden_walker_widget(widget: WidgetT) -> WidgetT:
    """
    Stop the browser requests `widget` handles from reaching outside the app: it refuses
    a visitor-supplied Kanaries token (see `_WALKER_TOKEN_MESSAGE`), rejects the actions
    in `_WALKER_BLOCKED_ACTIONS`, and validates the SQL of the actions in
    `_WALKER_SQL_ACTIONS` (see `validate_visitor_sql`).

    Works on any PyGWalker widget, including one from `pygwalker.api.anywidget.walk()`,
    and is a no-op the second time round (widgets can be rendered again).
    """
    comm = walker_comm(widget)
    if comm is None:
        raise RuntimeError(
            "Can't secure this PyGWalker widget: shinywidgets can't find its request "
            "handlers. This usually means the installed pygwalker version isn't "
            "supported; please report it at "
            "https://github.com/posit-dev/py-shinywidgets/issues"
        )

    handlers = comm._endpoint_map
    upload_spec_to_cloud = handlers.get("upload_spec_to_cloud")
    if upload_spec_to_cloud is not None and not getattr(
        upload_spec_to_cloud, "_shinywidgets_rejects_tokens", False
    ):

        def reject_browser_token(data: Dict[str, Any]) -> Any:
            if data.get("newToken"):
                raise RuntimeError(_WALKER_TOKEN_MESSAGE)
            return upload_spec_to_cloud(data)

        reject_browser_token._shinywidgets_rejects_tokens = True  # pyright: ignore[reportFunctionMemberAccess]
        comm.register("upload_spec_to_cloud", reject_browser_token)

    for action in _WALKER_BLOCKED_ACTIONS:
        comm.register(action, _reject_walker_action(action))

    for action in _WALKER_SQL_ACTIONS:
        handler = handlers.get(action)
        if handler is None or getattr(handler, "_shinywidgets_validates_sql", False):
            continue

        def validate_then_handle(
            data: Dict[str, Any],
            _handler: Callable[[Dict[str, Any]], Any] = handler,
            _action: str = action,
        ) -> Any:
            for sql in _walker_action_sql(_action, data):
                validate_visitor_sql(sql)
            return _handler(data)

        validate_then_handle._shinywidgets_validates_sql = True  # pyright: ignore[reportFunctionMemberAccess]
        comm.register(action, validate_then_handle)

    return widget


def _walker_action_sql(action: str, data: Dict[str, Any]) -> List[str]:
    """The SQL strings a `_WALKER_SQL_ACTIONS` handler would run."""
    if action == "batch_get_datas_by_sql":
        return [sql for sql in data.get("queryList", []) if isinstance(sql, str)]
    sql = data.get("sql")
    return [sql] if isinstance(sql, str) else []


def validate_visitor_sql(sql: str) -> None:
    """
    Raise unless `sql` (sent by a PyGWalker browser) is a single SELECT that reads
    only the widget's own data.

    PyGWalker runs the SQL its browser sends on DuckDB's default connection, which
    every PyGWalker widget in the process shares, so a visitor's query may reference
    the widget's registered view and its own CTEs only: no DDL (a ``CREATE TABLE``
    would persist in the shared database for every visitor to read), no other
    statements, and no other tables or views. Reading outside DuckDB (e.g.,
    ``read_csv``) is covered separately: the renderer requires the connection to be
    locked down first (see `require_duckdb_lockdown`).
    """
    import sqlglot  # pyright: ignore[reportMissingImports]
    from sqlglot import exp  # pyright: ignore[reportMissingImports]

    try:
        statements = sqlglot.parse(sql, dialect="duckdb")
    except Exception:
        statements = []
    if len(statements) != 1 or statements[0] is None:
        raise RuntimeError(_WALKER_SQL_MESSAGE)
    statement = statements[0]
    while isinstance(statement, (exp.Subquery, exp.Paren)):
        statement = statement.this
    if not isinstance(statement, (exp.Select, exp.Union, exp.Except, exp.Intersect)):
        raise RuntimeError(_WALKER_SQL_MESSAGE)
    cte_names = {cte.alias for cte in statement.find_all(exp.CTE)}
    for table in statement.find_all(exp.Table):
        if table.name != _WALKER_TABLE_NAME and table.name not in cte_names:
            raise RuntimeError(_WALKER_SQL_MESSAGE)


def _reject_walker_action(action: str) -> Callable[[Dict[str, Any]], Any]:
    def reject(_: Dict[str, Any]) -> Any:
        raise RuntimeError(
            f"shinywidgets doesn't allow PyGWalker's '{action}' action in a Shiny app."
        )

    return reject


def is_dataframe(x: object, pkg: str) -> bool:
    return any(
        widget_pkg(cls) == pkg and cls.__name__ == "DataFrame"
        for cls in type(x).__mro__
    )


class render_quak(render_widget_base[ValueT, QuakWidget]):
    """
    Reactively render a [quak](https://github.com/manzt/quak) data table as a Shiny
    output.

    The decorated function may return either a DataFrame-like object (e.g., a pandas
    or polars `DataFrame`, or a pyarrow `Table`), which is coerced to a `quak.Widget`
    (requires ``pip install 'shinywidgets[quak]'``), or a `quak.Widget`. In a filling
    layout, the table grows to fit its container.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `quak.Widget` instance. Use `.widget` to reactively read the table's state with
    :func:`~shinywidgets.reactive_read`: `reactive_read(table.widget, "sql")` is the
    SQL query for the table's current sort and filter state, and
    `table.widget.data()` runs it, returning a DuckDB relation of the matching rows.
    The query is an empty string while the table starts up (so guard with
    ``req(reactive_read(table.widget, "sql"))``), and it's read-only: setting it from
    Python doesn't change the table.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """

    # DataFrames are a generic type that several renderers accept, so rather than
    # registering them in AS_WIDGET_MAP, coerce them here
    def _as_widget(self, value: ValueT) -> QuakWidget:
        if isinstance(value, Widget):
            return super()._as_widget(value)

        try:
            import quak  # pyright: ignore[reportMissingImports]
        except ImportError:
            raise ImportError(
                "Install the quak package to use render_quak with shinywidgets (pip install 'shinywidgets[quak]')."
            )

        return quak.Widget(value)


class render_vizarr(render_widget_base[ValueT, VizarrViewer]):
    """
    Reactively render a [vizarr](https://github.com/hms-dbmi/vizarr) image viewer
    (for OME-NGFF/Zarr bioimages) as a Shiny output.

    The decorated function should return a `vizarr.Viewer` with one or more images
    added via ``.add_image()`` (requires ``pip install 'shinywidgets[vizarr]'``).
    In a filling layout, the viewer grows or shrinks to fit its container.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `vizarr.Viewer` instance. Use `.widget` to programmatically update the rendered
    viewer in place (e.g., ``.widget.add_image(...)`` adds a layer without a full
    re-render, and ``.widget.view_state = {...}`` sets the camera; trait changes on
    the widget are synced to the browser), or to reactively read viewer state with
    :func:`~shinywidgets.reactive_read`.

    Note
    ---
    **Data sources**: ``add_image()`` accepts a remote URL string (e.g., an
    OME-Zarr store on S3), which the browser fetches directly, or a local
    `zarr.Array`/`zarr.Group`/store/numpy array, in which case chunks are served
    on demand over the widget comm (base64-encoded, since Shiny has no binary
    message channel). Prefer remote URLs for large images: they avoid the ~33%
    base64 inflation and keep chunk traffic off the Shiny websocket.

    **Reactive state**: panning and zooming syncs the camera to the ``view_state``
    trait (a dict with ``target`` and ``zoom``, debounced ~200ms), so it can drive
    reactive calculations (e.g., ``reactive_read(vz.widget, "view_state")``).
    Setting ``.widget.view_state`` from Python moves the camera. Note that the
    layer controls in the viewer's side panel (channel colors, contrast limits,
    visibility) do *not* sync back to Python.

    **Sizing**: in a filling layout the viewer grows or shrinks to fit its
    container, and an explicit ``output_widget(height=...)`` sizes the viewer to
    that height. Otherwise the viewer's own ``height`` trait applies (default
    ``"500px"``); setting it (e.g., ``vizarr.Viewer(height="300px")``) opts out
    of filling, and an explicit ``output_widget(height=...)`` takes precedence
    over it.

    **Network access**: the widget loads its JavaScript (the vizarr viewer and
    viv) from CDNs at render time, so it requires an internet connection.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.
    """


def dataframe_to_keplergl(df: pd.DataFrame) -> KeplerGl:
    # keplergl 0.3.x imports pkg_resources, which setuptools >= 82 no longer ships
    hint = "pip install 'shinywidgets[keplergl]'"
    try:
        from keplergl import KeplerGl
    except ModuleNotFoundError as e:
        if e.name == "keplergl":
            raise ImportError(
                f"Install the keplergl package to use kepler.gl with shinywidgets ({hint})."
            )
        raise ImportError(
            f"keplergl failed to import (missing module {e.name!r}); "
            f"@render_keplergl requires keplergl>=0.4.0rc4 ({hint})."
        ) from e

    if Version(package_version("keplergl")) < Version("0.4.0rc4"):
        raise ImportError(
            f"@render_keplergl requires keplergl>=0.4.0rc4, but {package_version('keplergl')} "
            f"is installed ({hint})."
        )

    import pandas as pd

    # Arrow would send an index other than a RangeIndex as an extra column,
    # which kepler.gl shows as a field (keplergl's JSON serialization drops it)
    if not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index(drop=True)

    # Unlike keplergl's default JSON serialization, Arrow keeps missing values
    # (NaN isn't valid JSON) and is more compact
    return KeplerGl(data={"data": df}, use_arrow=True)


class render_rerun(render_widget_base[RerunValueT, RerunNotebookViewer]):
    """
    Reactively render a [rerun](https://rerun.io) viewer as a Shiny output.

    rerun is a multimodal viewer for time-indexed data: you log 3D scenes,
    images, tensors, timeseries, or text logs from Python, and the viewer lets
    you scrub a timeline to see how it all evolved. Data logged to the viewer's
    recording streams live to the browser, both during the initial render and
    from later reactive updates.

    The decorated function may return either a `rerun.notebook.Viewer` (the
    recommended, high-level API; it is coerced to its inner widget) or a
    `rerun_notebook.Viewer` widget directly. Both require ``pip install
    'shinywidgets[rerun]'``.

    .. important::
        Create the `rerun.RecordingStream` inside the render function and pass
        it to the viewer (``Viewer(recording=...)``), so each session gets its
        own recording. rerun's usual ``rr.init()`` + ``rr.log()`` pattern
        writes to a single process-global recording. That's fine in Jupyter,
        where one kernel serves one person, but a Shiny process serves every
        browser session at once -- with a global recording, one user's data
        would appear in every other user's viewer.

    Note that ``rr.notebook_show()`` does not work in Shiny: it renders through
    Jupyter's display machinery (which Shiny never invokes), and it *drains*
    the recording, producing a one-shot snapshot with no live updates. Always
    construct a `rerun.notebook.Viewer` and return it from the render function
    instead -- the viewer then stays connected, and data logged later streams
    in live.

    The decorated function also gains two read-only attributes: `.value`, the
    value most recently returned by the render function, and `.widget`, the
    rendered `rerun_notebook.Viewer` widget. Since `.widget` is the low-level
    widget (not the `rerun.notebook.Viewer` wrapper), keep a reference to the
    wrapper if you want to call its methods (`update_panels()`,
    `set_time_ctrl()`, `send_table()`, ...) from later reactive updates.
    Python-side trait updates (e.g., ``widget._width = 800``) also stream to
    the browser.

    To react to viewer interactions (play/pause, timeline scrubbing, selection
    changes), register a callback with `rerun.notebook.Viewer.on_event()` and
    set a `shiny.reactive.Value` inside it. These interactions reach Python as
    one-off messages, not as synced widget state, so
    :func:`~shinywidgets.reactive_read` can't see them -- it only reads synced
    traits. rerun keeps high-frequency interactions off the synced-trait
    channel by design (syncing every timeline tick would be expensive), and the
    explicit callback lets you choose which events are worth reacting to:

    ```python
    from shiny import reactive

    selection = reactive.Value(None)


    @render_rerun
    def viewer():
        rec = rr.RecordingStream(application_id="my_app")
        v = rr.notebook.Viewer(recording=rec)
        v.on_event(lambda evt: selection.set(evt))
        return v
    ```

    In a filling layout, the viewer fills its container when its width/height
    are left at their defaults (or set to ``"auto"``); an explicit integer
    ``width=``/``height=`` is respected instead. An explicit
    ``output_widget(height=...)`` also fits the default-sized viewer to the
    output's height. The viewer's JavaScript/Wasm
    bundle (~55MB) loads from rerun's CDN by default; set the
    ``RERUN_NOTEBOOK_ASSET`` environment variable to ``serve-local`` or
    ``inline`` to serve it from the Shiny process instead (see the
    [rerun-notebook docs](https://pypi.org/project/rerun-notebook/)).
    Note that ``serve-local`` starts a loopback (``localhost``) server inside
    the Shiny process, so the browser can only reach it when it runs on the
    same host as the app (e.g., local development). For remote deployments,
    use ``inline`` instead, unless the asset server is proxied to the client.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Examples
    --------
    ```python
    import numpy as np
    import rerun as rr
    from rerun.notebook import Viewer
    from shiny.express import ui
    from shinywidgets import render_rerun


    @render_rerun
    def viewer():
        rec = rr.RecordingStream(application_id="my_app")
        rec.log("points", rr.Points3D(np.random.rand(100, 3)))
        return Viewer(width="auto", height="auto", recording=rec)
    ```
    """


class render_pyvista(render_widget_base[PyvistaValueT, PyvistaHtmlWidget]):
    """
    Reactively render a [pyvista](https://pyvista.org) 3D plot as a Shiny output.

    The decorated function may return either a `pyvista.Plotter` (which is
    coerced to an ipywidget via pyvista's ``jupyter_backend="html"`` export;
    requires ``pip install 'shinywidgets[pyvista]'``) or the exported
    `trame_pyvista.jupyter.EmbeddableWidget` itself. In a filling layout, the
    view fills its container unless an explicit ``height`` is given. On a
    headless server, set ``pyvista.OFF_SCREEN = True`` before plotting.

    Return the `Plotter` itself -- do not call `Plotter.show()`. Outside
    Jupyter, `show()` ignores ``jupyter_backend``, returns `None`, and the
    output renders nothing. If you pre-build the widget (e.g., via
    ``trame_pyvista.jupyter.show_trame(pl, mode="html")``), pass
    ``width="100%", height="100%"`` or it keeps the plotter's pixel
    ``window_size`` instead of filling the container.

    The export is a self-contained, client-side vtk.js view: camera
    interaction (rotate/zoom/pan) happens entirely in the browser, and no
    widget state is synced back to Python, so there is nothing to read with
    :func:`~shinywidgets.reactive_read`. Each render embeds the entire scene
    in the widget state (roughly 1 MB even for a trivial mesh, growing with
    scene size), so prefer fewer, larger re-renders over frequent small ones.
    For fully server-driven interactivity (e.g., picking, server-side
    rendering), use pyvista's ``jupyter_backend="trame"`` with a trame server
    embedded via ``shiny.ui.tags.iframe`` instead (shinywidgets can't host
    trame's websocket server).

    The decorated function also gains two read-only attributes: `.value`, the
    value most recently returned by the render function, and `.widget`, the
    rendered `EmbeddableWidget` instance. Note that, unlike most other
    ``render_*`` decorators, the widget has no live connection to the plotter,
    so the scene can't be updated in place via `.widget` -- re-render instead.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Examples
    --------
    ```python
    import pyvista as pv
    from shiny import App, ui
    from shinywidgets import output_widget, render_pyvista

    pv.OFF_SCREEN = True

    app_ui = ui.page_fillable(output_widget("plot"))


    def server(input, output, session):
        @render_pyvista
        def plot():
            pl = pv.Plotter()
            pl.add_mesh(pv.Sphere(), show_edges=True)
            return pl


    app = App(app_ui, server)
    ```
    """


class render_niivue(render_widget_base[ValueT, NiiVue]):
    """
    Reactively render a [NiiVue](https://niivue.com) neuroimaging viewer
    (volumes, overlays, and meshes) as a Shiny output, via
    [ipyniivue](https://github.com/niivue/ipyniivue).

    The decorated function should return an `ipyniivue.NiiVue` widget with
    volumes and/or meshes loaded (requires ``pip install
    'shinywidgets[niivue]'``). In a filling layout, the viewer grows or
    shrinks to fit its container (tracking resizes, including
    ``full_screen``); an explicit ``output_widget(height=...)`` is respected
    too. Don't pass ``height=`` to `NiiVue()` itself -- it sets the canvas's
    pixel height, which disagrees with the output's height and causes
    clipping or dead space.

    The decorated function also gains two read-only attributes: `.value`, the
    value most recently returned by the render function, and `.widget`, the
    rendered `NiiVue` instance. Use `.widget` to update the viewer in place
    without a re-render: ``.widget.set_colormap(volume_id, name)``,
    ``.widget.set_opacity(index, value)``, ``.widget.set_gamma(value)``,
    ``.widget.set_slice_type(SliceType.RENDER)``, and
    ``.widget.move_crosshair_in_vox(dx, dy, dz)`` all apply live (trait
    changes on the widget are synced to the browser).

    Note
    ---
    **Reading the crosshair**: the crosshair position does *not* sync back
    as a trait (``reactive_read(nv.widget.scene, "crosshair_pos")`` never
    updates). Instead, register a callback with
    ``@nv.on_location_change`` inside the render function and have it set a
    session-scoped `reactive.Value` -- the payload includes fractional and
    millimeter coordinates and the voxel intensities under the crosshair.
    (Beware: exceptions raised inside these callbacks are swallowed by
    ipywidgets, so a failing callback just looks like "no updates".)
    Similarly, ``nv.frac2mm()``/``nv.mm2frac()`` don't work on Shiny (the
    coordinate matrices exist only in the browser); use the millimeter
    coordinates from the `on_location_change` payload instead.

    **Data size**: each render sends the viewer's JavaScript bundle (~5 MB)
    plus every volume (base64-encoded) to the browser, and the browser
    uploads the decoded voxels back to Python, so re-renders are expensive
    for large volumes. Prefer `Volume(url=...)` for remote data (the
    browser fetches it directly), and prefer in-place ``.widget.set_*``
    updates over re-rendering.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    width
        A CSS length unit (e.g., ``"400px"`` or ``"100%"``) for the output's width.
    height
        A CSS length unit for the output's height. When ``None`` (the default), the
        output is designed to fill the height of its parent container (see ``fill``
        and ``fillable``).
    fill
        Whether the output should grow or shrink to fit its parent container. When
        ``None`` (the default), this is ``True`` if ``height`` is not specified.
    fillable
        Whether the output container should fill available space (scrolling its
        contents on overflow). When ``None`` (the default), this is ``True`` if
        ``height`` is not specified.

    Examples
    --------
    ```python
    from ipyniivue import NiiVue, Volume
    from shiny import App, reactive, render, ui
    from shinywidgets import output_widget, render_niivue

    app_ui = ui.page_fluid(
        output_widget("brain"),
        ui.output_text_verbatim("crosshair"),
    )


    def server(input, output, session):
        location = reactive.Value("Click the brain to inspect a voxel")

        @render_niivue
        def brain():
            nv = NiiVue()
            nv.load_volumes(
                [Volume(url="https://niivue.com/demos/images/mni152.nii.gz")]
            )

            @nv.on_location_change
            def _(loc):
                location.set(loc["string"])

            return nv

        @render.text
        def crosshair():
            return location()


    app = App(app_ui, server)
    ```
    """
