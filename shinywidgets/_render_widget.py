from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, TypeVar, Union, cast

from htmltools import Tag

if TYPE_CHECKING:
    import plotly.graph_objects as go
    from altair import JupyterChart
    from ipympl.backend_nbagg import Canvas as MplCanvas
    from jupyter_bokeh import BokehModel
    from maplibre.ipywidget import MapWidget
    from plotly.graph_objects import FigureWidget
    from pydeck.widget import DeckGLWidget
    from pygwalker.api.anywidget import _WalkerWidget as WalkerWidget
else:
    JupyterChart = MplCanvas = BokehModel = MapWidget = FigureWidget = DeckGLWidget = (
        WalkerWidget
    ) = object

from ._bokeh import bokeh_dependency
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

__all__ = (
    "render_widget",
    "render_altair",
    "render_bokeh",
    "render_holoviews",
    "render_maplibre",
    "render_matplotlib",
    "render_panel",
    "render_plotly",
    "render_pydeck",
    "render_pygwalker",
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


class render_maplibre(render_widget_base[ValueT, MapWidget]):
    """
    Reactively render a [maplibre](https://eoda-dev.github.io/py-maplibregl/) map as a
    Shiny output.

    The decorated function may return either a `maplibre.Map` (which is coerced to a
    `maplibre.ipywidget.MapWidget`; requires ``pip install 'maplibre[anywidget]'``)
    or a `maplibre.ipywidget.MapWidget` widget.

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `MapWidget` instance. Use `.widget` to programmatically update the rendered map
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

    The decorated function also gains two read-only attributes: `.value`, the value
    most recently returned by the render function, and `.widget`, the rendered
    `BokehModel` instance. Use `.widget` to programmatically update the rendered
    plot in place (trait changes on the widget are synced to the browser), or to
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


class render_pygwalker(render_widget_base[ValueT, WalkerWidget]):
    """
    Reactively render a [PyGWalker](https://docs.kanaries.net/pygwalker) data
    exploration app as a Shiny output.

    The decorated function may return either a pandas `DataFrame` (which is coerced to
    a PyGWalker widget; requires ``pip install pygwalker``) or a widget created by
    `pygwalker.api.anywidget.walk()` (use this to pass options like ``theme_key``).
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
    including SQL that reads or writes files on the server. In deployed apps, lock
    that connection down when the app starts (this also applies to any other code in
    the process that uses ``duckdb.sql()`` and friends without a connection):

    ```python
    import duckdb

    # Set first: PyGWalker sets it per query, which a locked configuration refuses
    duckdb.execute("SET TimeZone = 'UTC'")
    duckdb.execute("SET enable_external_access = false")
    duckdb.execute("SET lock_configuration = true")
    ```

    Even then, the explorer is best suited to trusted users: a visitor can still send
    expensive queries, which block the Python process while they run.

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
        if is_dataframe(value, "polars"):
            raise TypeError(
                "PyGWalker's polars support is broken with polars >= 1.0. "
                "Pass a pandas DataFrame instead (e.g., df.to_pandas())."
            )
        if not is_dataframe(value, "pandas"):
            return super()._as_widget(value)

        try:
            from pygwalker.api.anywidget import walk
        except ImportError:
            raise ImportError(
                "Install the pygwalker package to use PyGWalker with shinywidgets (pip install pygwalker)."
            )

        return walk(value)


def is_dataframe(x: object, pkg: str) -> bool:
    return any(
        widget_pkg(cls) == pkg and cls.__name__ == "DataFrame"
        for cls in type(x).__mro__
    )
