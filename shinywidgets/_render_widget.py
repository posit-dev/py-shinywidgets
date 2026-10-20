from __future__ import annotations

from typing import TYPE_CHECKING, Optional, cast

from htmltools import Tag

if TYPE_CHECKING:
    from altair import JupyterChart
    from jupyter_bokeh import BokehModel
    from maplibre.ipywidget import MapWidget
    from plotly.graph_objects import FigureWidget
    from pydeck.widget import DeckGLWidget
else:
    JupyterChart = BokehModel = MapWidget = FigureWidget = DeckGLWidget = object

from ._bokeh import bokeh_dependency
from ._render_widget_base import ValueT, WidgetT, render_widget_base
from .types import PlotlyConfig

__all__ = (
    "render_widget",
    "render_altair",
    "render_bokeh",
    "render_holoviews",
    "render_maplibre",
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

    The decorated function should return an `altair.Chart` (or an
    `altair.JupyterChart`), which is coerced to a `JupyterChart` widget.

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

    The decorated function should return a `maplibre.Map`, which is coerced to a
    `maplibre.ipywidget.MapWidget` (requires ``pip install 'maplibre[anywidget]'``).

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

    The decorated function should return a bokeh model (e.g., a
    `bokeh.plotting.figure`), which is coerced to a `jupyter_bokeh.BokehModel` widget
    (requires ``pip install jupyter_bokeh``).

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

    The decorated function should return a panel pane or viewable, which is rendered
    through bokeh (requires ``pip install panel``).

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

    The decorated function should return a holoviews/hvplot object, which is rendered
    through panel (requires ``pip install panel``).

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


class render_plotly(render_widget_base[ValueT, FigureWidget]):  # pyright: ignore[reportInvalidTypeArguments]
    """
    Reactively render a [plotly](https://plotly.com/python/) figure as a Shiny output.

    The decorated function should return a `plotly.graph_objects.Figure`, which is
    coerced to a `FigureWidget`. Alternatively, it may return a Dash-style
    `(figure, config)` tuple, where `config` is a dict of Plotly.js [config
    options](https://plotly.com/javascript/configuration-options/) (e.g.,
    `{"displayModeBar": False}`), mirroring Dash's `dcc.Graph(figure=..., config=...)`
    API. The config is merged over plotly's defaults, so it also takes precedence over
    shinywidgets' own defaults (e.g., `responsive`).

    The output's `.value` attribute is exactly what the render function returned (a
    figure, or the `(figure, config)` tuple), while `.widget` is always the coerced
    `FigureWidget` (with `config` merged into its ``_config`` trait). For type
    annotations, :data:`~shinywidgets.types.PlotlyValue` (equivalently,
    `PlotlyFigure`) and :data:`~shinywidgets.types.PlotlyConfig` describe the
    supported return shape.

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

    def _as_widget(self, value: ValueT) -> FigureWidget:
        fig, config = _split_config(value)
        widget = super()._as_widget(cast(ValueT, fig))
        if config:
            widget._config = {**widget._config, **config}  # type: ignore
        return widget


def _split_config(value: object) -> tuple[object, Optional[PlotlyConfig]]:
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

    The decorated function should return a `pydeck.Deck`, which is coerced to a
    `pydeck.widget.DeckGLWidget` (requires pydeck <= 0.8, since pydeck v0.9 removed
    ipywidgets support).

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
