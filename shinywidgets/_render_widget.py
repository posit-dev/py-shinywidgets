from __future__ import annotations

import inspect
import re
import sys
import warnings
from functools import lru_cache, partial
from importlib.metadata import version as package_version
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, TypeVar, Union, cast

from htmltools import Tag
from ipywidgets.widgets.widget import Widget
from packaging.version import Version

if TYPE_CHECKING:
    import pandas as pd
    import plotly.graph_objects as go
    from altair import JupyterChart
    from bqplot import Figure as BqplotFigure
    from ipyaladin import Aladin
    from ipycanvas import Canvas as IpycanvasCanvas
    from ipycanvas import MultiCanvas, MultiRoughCanvas, RoughCanvas
    from ipycytoscape import CytoscapeWidget
    from ipydatagrid import DataGrid
    from ipyleaflet import Map as LeafletMap
    from ipympl.backend_nbagg import Canvas as MplCanvas
    from ipysigma import Sigma
    from itables.widget import ITable
    from jscatter.widget import JupyterScatter
    from jupyter_bokeh import BokehModel
    from keplergl import KeplerGl
    from lonboard import Map as LonboardMap  # pyright: ignore[reportMissingImports]
    from maplibre.ipywidget import MapWidget
    from maplibre.map import Map as MaplibreMap
    from mols2grid.molgrid import MolGrid
    from mosaic_widget import MosaicWidget
    from perspective.widget import PerspectiveWidget
    from plotly.graph_objects import FigureWidget
    from pydeck.widget import DeckGLWidget
    from quak import Widget as QuakWidget
else:
    JupyterChart = DataGrid = ITable = JupyterScatter = KeplerGl = MplCanvas = Sigma = (
        BokehModel
    ) = MapWidget = FigureWidget = DeckGLWidget = MosaicWidget = BqplotFigure = (
        CytoscapeWidget
    ) = base = LeafletMap = object
    Aladin = IpycanvasCanvas = MultiCanvas = MultiRoughCanvas = RoughCanvas = (
        LonboardMap
    ) = QuakWidget = PerspectiveWidget = MolGrid = object

from ipywidgets.widgets import HTML, Box, Layout
from shiny.render.renderer import Jsonifiable, ValueFn
from shiny.session import get_current_session

from ._as_widget import (
    PYDECK_NO_WIDGET_MESSAGE,
    as_widget_panel,
    networkx_to_sigma,
    perspective_widget,
    pydeck_has_widget,
)
from ._bokeh import _bokeh_dependency
from ._dependencies import widget_pkg
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
# String bound: mols2grid (and pandas) are optional dependencies.
Mols2GridValueT = TypeVar("Mols2GridValueT", bound="Union[MolGrid, pd.DataFrame]")

__all__ = (
    "render_widget",
    "render_altair",
    "render_bokeh",
    "render_bqplot",
    "render_holoviews",
    "render_ipyaladin",
    "render_ipycanvas",
    "render_ipycytoscape",
    "render_ipydatagrid",
    "render_ipyleaflet",
    "render_ipysigma",
    "render_itables",
    "render_jscatter",
    "render_keplergl",
    "render_leafmap",
    "render_lonboard",
    "render_maplibre",
    "render_matplotlib",
    "render_mols2grid",
    "render_mosaic_widget",
    "render_panel",
    "render_perspective",
    "render_plotly",
    "render_plotnine",
    "render_pydeck",
    "render_quak",
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
    **Selections and params**: name your selections and params (e.g.,
    ``alt.selection_interval(name="brush")``), then read them with
    ``reactive_read(chart.widget.selections, "brush").value``, or observe them on a
    `JupyterChart` you build yourself (``jchart.selections.observe(fn, ["brush"])``).
    Selections can't be set from Python, but params can: setting
    ``chart.widget.params.<name> = value`` updates the chart in place without
    re-sending its data. To throttle how often selections update Python while
    dragging, return ``alt.JupyterChart(chart, debounce_wait=150)``. Prefer params
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
    """


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
    `ITable` instance. Use `.widget` to programmatically update the rendered table
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
    """

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
    `JupyterScatter` instance. Use `.widget` to programmatically update the rendered
    plot in place (trait changes on the widget are synced to the browser), or to
    reactively read widget state (e.g., the selected points via ``"selection"``) with
    :func:`~shinywidgets.reactive_read`. The selection is an array of row *positions*
    (use ``df.iloc[...]``), not index labels.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Note
    ---
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
    """


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

    The PanZoom and Reset buttons of a figure's built-in toolbar don't work in Shiny
    (they create widgets from the browser, which shinywidgets doesn't support); pass
    ``display_toolbar=False`` to the figure to hide the toolbar, and set
    ``fig.interaction = bqplot.interacts.PanZoom(...)`` from Python to enable panning
    and zooming.

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
    `BokehModel` instance. Bokeh model properties are not widget traits, so instead
    of :func:`~shinywidgets.reactive_read`, use bokeh's own callbacks to react to user
    interaction (e.g., ``source.selected.on_change("indices", lambda attr, old, new:
    selected.set(new))``, or ``fig.on_event(Tap, ...)``). These callbacks may set
    `reactive.value`s. To update the plot without re-rendering, modify the bokeh
    models in place (e.g., ``source.data = ...``). Plots that share a
    `ColumnDataSource` (e.g., for linked selection) must be returned together, in
    one layout, from a single render function. Create bokeh models per session
    (e.g., inside the render function), not at the top level of a Shiny Core app,
    where every visitor would share them.

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
    **Events**: to respond to user interaction, return a `go.FigureWidget` and
    register plotly callbacks on it (e.g., ``fig.data[0].on_click(fn)``,
    ``fig.data[0].on_selection(fn)``, or ``fig.layout.xaxis.on_change(fn,
    "range")``), typically setting a `reactive.value` inside the callback.
    Callbacks registered on a `go.Figure` don't carry over when it's coerced to a
    `FigureWidget`, so they never fire.

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
    """

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
    ):
        warnings.warn(
            "render_pydeck is deprecated: pydeck v0.9 removed its Jupyter widget, so "
            "it can't render maps. Pass pydeck.Layer objects to a maplibre Map's "
            "add_deck_layers() and use @render_maplibre instead (see "
            "help(shinywidgets.render_pydeck) for other alternatives).",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(_fn, width=width, height=height, fill=fill, fillable=fillable)

    def _as_widget(self, value: ValueT) -> DeckGLWidget:
        # A DeckGLWidget (which as_widget() passes through) can't render either
        if not pydeck_has_widget():
            raise TypeError(PYDECK_NO_WIDGET_MESSAGE)
        return super()._as_widget(value)


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
            import quak
        except ImportError:
            raise ImportError(
                "Install the quak package to use render_quak with shinywidgets (pip install 'shinywidgets[quak]')."
            )

        return quak.Widget(value)


class render_mols2grid(render_widget_base[Mols2GridValueT, Widget]):
    """
    Reactively render a [mols2grid](https://mols2grid.readthedocs.io) molecule
    grid as a Shiny output.

    The decorated function may return either a `mols2grid.MolGrid`, or a
    `pandas.DataFrame` with a SMILES column (``smiles_col``, ``"SMILES"`` by
    default) or an RDKit molecule column (``mol_col``), which is coerced to a
    `MolGrid` (requires ``pip install 'shinywidgets[mols2grid]'``). Don't return
    the object returned by ``mols2grid.display()`` -- it's an IPython HTML
    object, not a grid.

    Extra keyword arguments are forwarded to mols2grid, split the way
    ``mols2grid.display()`` splits them: the rendering options (``subset``,
    ``tooltip``, ``sort_by``, ``n_items_per_page``, ``selection``,
    ``custom_css``, ``transform``, ``callback``, ...) go to the grid's
    rendering, and everything else goes to `MolGrid()` -- its constructor
    options (``size``, ``useSVG``, ``prerender``, ``cache_selection``,
    ``removeHs``, ``use_coords``, ``coordGen``, ``MolDrawOptions``, ``name``,
    ``rename``), or, for any other name, an RDKit draw option
    (``addStereoAnnotation=True``, ``addAtomIndices=True``, ...). The grid is
    always displayed in an iframe (``use_iframe=True``), which keeps its
    jQuery/Bootstrap globals out of your app's page.

    The decorated function also gains three read-only attributes: `.value`, the
    value most recently returned by the render function, `.widget`, the rendered
    `ipywidgets.Box` holding the output, and `.grid`, the `MolGrid` instance
    backing it. The `MolGridWidget` that syncs selection state is
    `.grid.widget`.

    * **Selection (browser -> Python):**
      ``ast.literal_eval(reactive_read(grid.grid.widget, "selection"))`` gives a
      dict of selected rows, e.g. ``{0: "CCO"}`` (the trait is a repr string
      with unquoted keys, not JSON, so parse it with `ast.literal_eval`, as
      mols2grid itself does). ``grid.grid.get_selection()`` returns the selected
      rows as a DataFrame.
    * **Filtering (Python -> browser):** ``grid.grid.filter(mask)`` (a boolean
      mask, Series, or list) hides non-matching molecules in the already
      rendered grid, without re-rendering. The mask is positional against the
      rows *as rendered* (mols2grid matches it up by each row's
      ``mols2grid-id``), so pass it in the DataFrame's row order -- a Series
      taken from a filtered or reordered frame hides the wrong molecules. Call
      it in response to user input: a filter issued while the grid is still
      loading is recorded on the widget's ``filter_mask`` trait but not applied
      by mols2grid's frontend (upstream limitation -- it applies the mask only
      when the trait *changes*, with no initial application and no retry), so a
      grid can't start out filtered: re-issue it once the grid is visible, and
      filter the DataFrame in the render function for a grid that is filtered
      from the start.
    * **Grid name**: mols2grid keys selections in a process-global registry,
      so grids coerced from a DataFrame get a name unique to the session and
      the output (a stable ``"shiny-<session>-<id>"`` slug, where the id is
      the output's *namespaced* id, so two module instances' ``grid`` outputs
      don't collide). A `MolGrid` you construct keeps its own ``name`` --
      give it a unique one (a grid still named ``"default"`` is rejected
      with an error, since it collides across sessions and across multiple
      grids on a page), and note that a `MolGrid` is itself process-global
      state, so construct it inside the render function, not at the top
      level of the app.
    * **Network access**: the grid's JavaScript (list.js, jQuery, RDKit
      MinimalLib, Bootstrap) loads from CDNs at render time, so the grid needs
      an internet connection (it renders empty, without an error, when the CDNs
      are unreachable). mols2grid hardcodes those URLs inside the iframe's
      document, so they can't be served from the app's own assets; if you need
      an offline or air-gapped deployment, please open an issue.
    * **Sizing**: the grid sizes its own height to fit its contents (mols2grid's
      ``fitIframe``), so it scrolls with the page rather than stretching to a
      filling container; an explicit ``height`` on the output acts as a viewport
      that clips the grid. Grid data is inlined into the iframe document
      (roughly 0.5-1 KB per molecule, depending on how many columns are
      shown), so grids in the tens of thousands of molecules can approach
      Shiny's default 16 MiB websocket message limit (raise it with ``shiny
      run --ws-max-size``). To bound the *grid* rather than
      its container, pass ``iframe_height`` (e.g.
      ``render_mols2grid(iframe_height="400px")``): it sets the iframe element's
      height, which switches off mols2grid's auto-fit so the grid scrolls
      inside the iframe. (``iframe_width``, ``iframe_allow``, and
      ``iframe_sandbox`` are forwarded to the iframe the same way.)

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Parameters
    ----------
    smiles_col
        The DataFrame column holding SMILES strings. Set to ``None`` when
        using ``mol_col`` instead.
    mol_col
        The DataFrame column holding RDKit molecules (e.g., from
        ``mols2grid.sdf_to_dataframe()``, which produces both). With
        ``smiles_col=None``, a SMILES column named ``"SMILES"`` is generated
        from the molecules (mols2grid itself mis-renders a ``None`` SMILES
        column).
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
    kwargs
        Extra keyword arguments forwarded to mols2grid (split between
        `MolGrid()` and its rendering, as described above). The split is by
        name and by mols2grid's own signatures: a name that the grid's
        rendering accepts (``subset``, ``tooltip``, ``sort_by``, ...) goes to
        the rendering, and any other name goes to `MolGrid()` -- so
        `render_mols2grid(addStereoAnnotation=True)` sets an RDKit draw option,
        the same passthrough ``mols2grid.display()`` provides.

    Examples
    --------
    ```python
    import ast

    import mols2grid
    from shiny import App, reactive, render, ui
    from shinywidgets import output_widget, reactive_read, render_mols2grid

    mols = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)

    app_ui = ui.page_fluid(
        output_widget("grid"),
        ui.output_text("n_selected"),
    )


    def server(input, output, session):
        @render_mols2grid(subset=["ID"], tooltip=["ID", "SOL"])
        def grid():
            return mols

        @render.text
        def n_selected():
            selection = ast.literal_eval(reactive_read(grid.grid.widget, "selection"))
            return f"{len(selection)} molecule(s) selected"


    app = App(app_ui, server)
    ```
    """

    def __init__(
        self,
        _fn: Optional[ValueFn[Mols2GridValueT]] = None,
        *,
        smiles_col: Optional[str] = "SMILES",
        mol_col: Optional[str] = None,
        width: Optional[str] = None,
        height: Optional[str] = None,
        fill: Optional[bool] = None,
        fillable: Optional[bool] = None,
        **kwargs: Any,
    ):
        super().__init__(_fn, width=width, height=height, fill=fill, fillable=fillable)
        self.smiles_col = smiles_col
        self.mol_col = mol_col
        # The rendering options (subset, tooltip, sort_by, ...) belong to the
        # grid's rendering, while everything else belongs to MolGrid(), whose
        # remaining **kwargs are RDKit draw options -- split them the way
        # mols2grid's own dispatch wrapper does, so that both
        # render_mols2grid(subset=[...]) and
        # render_mols2grid(addStereoAnnotation=True) just work
        render_params = _mols2grid_render_kwargs()
        self.render_kwargs: Dict[str, Any] = {
            key: val for key, val in kwargs.items() if key in render_params
        }
        self.grid_kwargs: Dict[str, Any] = {
            key: val for key, val in kwargs.items() if key not in render_params
        }
        self._grid: Optional[MolGrid] = None
        # Grid names this renderer has already registered a selection-registry
        # cleanup for (see _cleanup_selection_registry)
        self._selection_cleanup_names: set[str] = set()

    # The session- and namespace-qualified output id, captured when the decorated
    # function is registered (see __call__). `output_id` alone isn't unique: two
    # module instances in one session can each have an output named "grid"
    _grid_output_id: Optional[str] = None

    def __call__(
        self, _fn: ValueFn[Mols2GridValueT]
    ) -> "render_mols2grid[Mols2GridValueT]":
        super().__call__(_fn)
        session = get_current_session()
        if session is not None and not session.is_stub_session():
            # A module's server function runs with its SessionProxy in context, so
            # that's where the namespace is known; rendering runs with the root
            # session, so this has to be captured now, not in as_grid()
            self._grid_output_id = str(session.ns(self.output_id))
        return self

    @property
    def grid(self) -> Optional[MolGrid]:
        """
        The `mols2grid.MolGrid` most recently rendered (read-only). Read it
        reactively like `.value`/`.widget`; use `.grid.widget` (the
        `MolGridWidget`) for `reactive_read()`.
        """
        return self._get_reactive_obj(self._grid)

    @grid.setter
    def grid(self, grid: object):
        raise RuntimeError(
            "The `grid` attribute of a @render_mols2grid function is read only."
        )

    async def _render(self) -> Jsonifiable | None:
        # Reset before rendering, so `.grid` mirrors `.value`/`.widget` (readers
        # are invalidated by the base render before a new grid is set)
        self._grid = None
        return await super()._render()

    def as_grid(self, value: Mols2GridValueT) -> MolGrid:
        try:
            from mols2grid import MolGrid
        except ImportError:
            raise ImportError(
                "Install the mols2grid package to use render_mols2grid with shinywidgets (pip install 'shinywidgets[mols2grid]')."
            )

        if isinstance(value, MolGrid):
            # A user-supplied MolGrid keeps its own name; mols2grid's default
            # name lives in a process-global selection registry, so it collides
            # across sessions (and across multiple grids on one page)
            if value.widget.grid_id == "default":
                raise ValueError(
                    "This mols2grid.MolGrid uses the default grid name ('default'), "
                    "which mols2grid stores in a process-global selection registry: "
                    "other sessions (and other grids on the same page) using the "
                    "same name would overwrite its selection, and this grid would "
                    "read theirs. Either construct it with a unique name "
                    "(mols2grid.MolGrid(df, name='my-grid')), or return the "
                    "DataFrame instead and pass any constructor options to the "
                    "decorator (e.g. @render_mols2grid(name='my-grid')), which "
                    "gives the grid a collision-free generated name."
                )
            return value
        if not is_pandas_dataframe(value):
            raise TypeError(
                "A @render_mols2grid render function should return a "
                f"mols2grid.MolGrid or a pandas.DataFrame, not an object of type "
                f"'{type(value).__name__}'. (Note that mols2grid.display() returns "
                "an IPython HTML object, which can't be rendered; return the "
                "MolGrid or DataFrame instead.)"
            )
        # A name passed to the decorator overrides the default, which is
        # unique per session *and* output: two grids in the same session share
        # the window, so a shared name would cross-wire their selections
        # (mols2grid keys models and lists by name on window)
        # (_grid_output_id/output_id are only set once the renderer decorates a
        # function)
        output_id = self._grid_output_id or getattr(self, "output_id", "grid")
        name = _MOLS2GRID_NAME_SLUG.sub("-", f"{grid_name()}-{output_id}")
        self._cleanup_selection_registry(name)
        grid_kwargs = {"name": name, **self.grid_kwargs}
        smiles_col = self.smiles_col
        if smiles_col is None:
            if self.mol_col is None:
                raise ValueError(
                    "One of `smiles_col` or `mol_col` must be set for "
                    "@render_mols2grid."
                )
            # mols2grid 2.2.0 creates a column named NaN (which its rendering
            # then chokes on) when smiles_col is None, so name the SMILES it
            # generates from the molecules instead
            smiles_col = "SMILES"
        return MolGrid(
            value,
            smiles_col=smiles_col,
            mol_col=self.mol_col,
            **grid_kwargs,
        )

    def _cleanup_selection_registry(self, name: str) -> None:
        """
        Drop this grid's entry from mols2grid's process-global selection registry when
        the session ends.

        mols2grid keys selections in a module-level dict that it never prunes (and its
        entries hold the selected rows), so a long-running server would otherwise keep
        one selection dict per session and grid output, forever. The name is unique to
        this session and output, so no other session can be using the entry.
        """
        if name in self._selection_cleanup_names:
            return
        self._selection_cleanup_names.add(name)
        session = get_current_session()
        if session is None or session.is_stub_session():
            return
        from mols2grid.select import register

        session.on_ended(partial(register.SELECTIONS.pop, name, None))

    def _as_widget(self, value: Mols2GridValueT) -> Widget:
        grid = self.as_grid(value)
        self._grid = grid

        render_kwargs = dict(self.render_kwargs)
        if not render_kwargs.pop("use_iframe", True):
            warnings.warn(
                "@render_mols2grid always renders the grid in an iframe "
                "(use_iframe=True), so the `use_iframe` argument is ignored.",
                stacklevel=3,
            )

        # MolGridWidget's own frontend is a 0x0 element that only bridges
        # selection/filter state; the grid itself is a separate HTML document.
        # mols2grid's marimo integration displays the two stacked, and an
        # ipywidgets Box does the same here. display() (rather than render())
        # escapes the document for the iframe's srcdoc attribute.
        iframe = grid.display(use_iframe=True, **render_kwargs)
        # The inner width hint is load-bearing: ipywidgets renders HTML as an
        # inline-flex container, so without it the iframe collapses to its
        # 300px replaced-element default instead of filling the output
        html = HTML(str(iframe.data), layout=Layout(width="100%"))
        return Box(
            [grid.widget, html],
            layout=Layout(width="100%", height="auto"),
        )


# What MolGrid's rendering accepts, per mols2grid 2.2.0 (the fallback for
# _mols2grid_render_kwargs() when mols2grid isn't importable yet, e.g. because
# the app is being rendered before the extra is installed)
_MOLS2GRID_RENDER_KWARGS_FALLBACK = frozenset(
    {
        "template",
        "subset",
        "tooltip",
        "tooltip_fmt",
        "tooltip_placement",
        "transform",
        "sort_by",
        "use_iframe",
        "truncate",
        "n_items_per_page",
        "selection",
        "substruct_highlight",
        "single_highlight",
        "border",
        "gap",
        "pad",
        "fontsize",
        "fontfamily",
        "textalign",
        "background_color",
        "hover_color",
        "custom_css",
        "style",
        "custom_header",
        "callback",
        "iframe_width",
        "iframe_height",
        "iframe_allow",
        "iframe_sandbox",
    }
)


@lru_cache(maxsize=1)
def _mols2grid_render_kwargs() -> frozenset[str]:
    """
    The kwargs that belong to a `MolGrid`'s *rendering*, rather than to `MolGrid()`
    itself.

    Derived from mols2grid's own signatures (rather than a hardcoded list, which a
    mols2grid upgrade would silently invalidate) so that everything else can be handed
    to `MolGrid()`, which is where its constructor options -- and, via its remaining
    ``**kwargs``, its RDKit draw options -- belong.
    """
    try:
        from mols2grid.molgrid import MolGrid
    except ImportError:
        return _MOLS2GRID_RENDER_KWARGS_FALLBACK

    # display() pops its own iframe options before forwarding to render(), which pops
    # `template` before forwarding to the matching to_<template>() method
    names: set[str] = {"template"}
    for member in ("display", "render", "to_interactive", "to_static"):
        fn = getattr(MolGrid, member, None)
        if fn is not None:
            names.update(set(inspect.signature(fn).parameters) - {"self", "kwargs"})
    return frozenset(names)


_MOLS2GRID_NAME_SLUG = re.compile(r"[^0-9a-zA-Z_-]+")


def grid_name() -> str:
    """
    A stable, session-unique mols2grid grid name.

    mols2grid keys selections by a process-global registry, so two sessions
    using the default name (``"default"``) clobber each other's selection.
    Keying on the Shiny session keeps sessions isolated while staying stable
    across re-renders, so that registry doesn't grow without bound.
    """
    session = get_current_session()
    raw = "shiny" if session is None else f"shiny-{session.id}"
    return _MOLS2GRID_NAME_SLUG.sub("-", raw).strip("-")


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
