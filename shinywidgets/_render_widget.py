from __future__ import annotations

import sys
import warnings
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
    from ipydatagrid import DataGrid
    from ipympl.backend_nbagg import Canvas as MplCanvas
    from ipysigma import Sigma
    from itables.widget import ITable
    from jscatter.widget import JupyterScatter
    from jupyter_bokeh import BokehModel
    from keplergl import KeplerGl
    from lonboard import Map as LonboardMap  # pyright: ignore[reportMissingImports]
    from maplibre.ipywidget import MapWidget
    from maplibre.map import Map as MaplibreMap
    from mosaic_widget import MosaicWidget
    from plotly.graph_objects import FigureWidget
    from pydeck.widget import DeckGLWidget
    from quak import Widget as QuakWidget
else:
    JupyterChart = DataGrid = ITable = JupyterScatter = KeplerGl = MplCanvas = Sigma = (
        BokehModel
    ) = MapWidget = FigureWidget = DeckGLWidget = MosaicWidget = BqplotFigure = object
    Aladin = IpycanvasCanvas = MultiCanvas = MultiRoughCanvas = RoughCanvas = (
        LonboardMap
    ) = QuakWidget = object

from shiny.render.renderer import ValueFn

from ._as_widget import (
    PYDECK_NO_WIDGET_MESSAGE,
    as_widget_panel,
    networkx_to_sigma,
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

__all__ = (
    "render_widget",
    "render_altair",
    "render_bokeh",
    "render_bqplot",
    "render_holoviews",
    "render_ipyaladin",
    "render_ipycanvas",
    "render_ipydatagrid",
    "render_ipysigma",
    "render_itables",
    "render_jscatter",
    "render_keplergl",
    "render_lonboard",
    "render_maplibre",
    "render_matplotlib",
    "render_mosaic_widget",
    "render_panel",
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
