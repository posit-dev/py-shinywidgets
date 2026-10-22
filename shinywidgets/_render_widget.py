from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, TypeVar, Union, cast

from htmltools import Tag
from ipywidgets.widgets.widget import Widget

if TYPE_CHECKING:
    import plotly.graph_objects as go
    from altair import JupyterChart
    from ipympl.backend_nbagg import Canvas as MplCanvas
    from jupyter_bokeh import BokehModel
    from lonboard import Map as LonboardMap  # pyright: ignore[reportMissingImports]
    from maplibre.ipywidget import MapWidget
    from maplibre.map import Map as MaplibreMap
    from plotly.graph_objects import FigureWidget
    from pydeck.widget import DeckGLWidget
else:
    JupyterChart = MplCanvas = BokehModel = MapWidget = FigureWidget = DeckGLWidget = (
        object
    )
    LonboardMap = object

from ._bokeh import bokeh_dependency
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

__all__ = (
    "render_widget",
    "render_altair",
    "render_bokeh",
    "render_holoviews",
    "render_lonboard",
    "render_maplibre",
    "render_matplotlib",
    "render_panel",
    "render_plotly",
    "render_pydeck",
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
    an `altair.JupyterChart` widget) or an `altair.JupyterChart` widget.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `JupyterChart` instance. Use `.widget` to programmatically update the rendered
    chart in place (trait changes on the widget are synced to the browser), or to
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


class render_lonboard(render_widget_base[ValueT, LonboardMap]):
    """
    Reactively render a [lonboard](https://developmentseed.org/lonboard/) map as a
    Shiny output.

    The decorated function may return a `lonboard.Map` widget, a lonboard layer (or a
    list of layers), which is placed on a `Map`, or any data that `lonboard.viz()`
    accepts (e.g., a GeoPandas `GeoDataFrame` or a GeoArrow-compatible Arrow table),
    which is converted to a `Map` via `lonboard.viz()` (requires ``pip install
    lonboard``). In a filling layout, the map fills its container unless the `Map`
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
                "Install the lonboard package to use render_lonboard with shinywidgets (pip install lonboard)."
            )

        # viz() handles lists of data, but not lists of layers
        if isinstance(value, (list, tuple)) and all(
            isinstance(x, lonboard.BaseLayer) for x in value
        ):
            m = lonboard.Map(value)
        else:
            m = lonboard.viz(value)
        return super()._as_widget(cast(ValueT, m))


class render_maplibre(render_widget_base[MaplibreValueT, MapWidget]):
    """
    Reactively render a [maplibre](https://eoda-dev.github.io/py-maplibregl/) map as a
    Shiny output.

    The decorated function may return either a `maplibre.Map` (which is coerced to a
    `maplibre.ipywidget.MapWidget`; requires ``pip install 'maplibre[anywidget]'``)
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
    widget. Figures and axes are coerced to a `Canvas` (requires ``pip install ipympl``),
    so this also works with libraries built on matplotlib (e.g., seaborn or
    ``pandas.DataFrame.plot()``). Figures created through pyplot are closed (via
    ``plt.close()``) when their widget is retired. In a filling layout, the figure is
    resized to fit its container.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `Canvas` instance. Use `.widget` to programmatically update the rendered figure
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


class render_bokeh(render_widget_base[ValueT, BokehModel]):
    """
    Reactively render a [bokeh](https://bokeh.org) plot as a Shiny output.

    The decorated function may return either a bokeh model (e.g., a
    `bokeh.plotting.figure`), which is coerced to a `jupyter_bokeh.BokehModel`
    widget, or a `jupyter_bokeh.BokehModel` widget (requires ``pip install
    jupyter_bokeh``).

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
        res.children.append(bokeh_dependency())
        return res


class render_panel(render_widget_base[ValueT, BokehModel]):
    """
    Reactively render a [panel](https://panel.holoviz.org) object as a Shiny output.

    The decorated function may return either a panel pane or viewable (which is
    rendered through bokeh; requires ``pip install panel``) or the underlying
    `jupyter_bokeh.BokehModel` widget.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `BokehModel` instance. Use `.widget` to programmatically update the rendered
    output in place (trait changes on the widget are synced to the browser), or to
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

    def auto_output_ui(self) -> Tag:
        res = super().auto_output_ui()
        res.children.append(bokeh_dependency())
        return res


class render_holoviews(render_widget_base[ValueT, BokehModel]):
    """
    Reactively render a [holoviews](https://holoviews.org) or
    [hvPlot](https://hvplot.holoviz.org) object as a Shiny output.

    The decorated function may return either a holoviews/hvplot object (which is
    rendered through panel; requires ``pip install panel``) or the underlying
    `jupyter_bokeh.BokehModel` widget.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `BokehModel` instance. Use `.widget` to programmatically update the rendered
    output in place (trait changes on the widget are synced to the browser), or to
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

    def auto_output_ui(self) -> Tag:
        res = super().auto_output_ui()
        res.children.append(bokeh_dependency())
        return res


class render_plotly(render_widget_base[PlotlyValueT, FigureWidget]):
    """
    Reactively render a [plotly](https://plotly.com/python/) figure as a Shiny output.

    The decorated function may return either a `plotly.graph_objects.Figure` (which
    is coerced to a `FigureWidget`) or a `plotly.graph_objects.FigureWidget` widget.
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
    rendered figure in place (trait changes on the widget are synced to the browser),
    or to reactively read widget state with :func:`~shinywidgets.reactive_read`.

    Use :func:`~shinywidgets.output_widget` in the UI to hold the output.

    Note
    ---
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
    Reactively render a [pydeck](https://pydeck.gl) map as a Shiny output.

    The decorated function may return either a `pydeck.Deck` (which is coerced to a
    `pydeck.widget.DeckGLWidget`) or a `pydeck.widget.DeckGLWidget` widget (requires
    pydeck <= 0.8, since pydeck v0.9 removed ipywidgets support).

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `DeckGLWidget` instance. Use `.widget` to programmatically update the rendered
    map in place (trait changes on the widget are synced to the browser), or to
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
