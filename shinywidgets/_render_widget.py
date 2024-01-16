from __future__ import annotations

from typing import TYPE_CHECKING

from ipywidgets.widgets import Widget  # pyright: ignore[reportMissingTypeStubs]

if TYPE_CHECKING:
    from altair import JupyterChart
    from jupyter_bokeh import BokehModel  # pyright: ignore[reportMissingTypeStubs]
    from plotly.graph_objects import (  # pyright: ignore[reportMissingTypeStubs]
        FigureWidget,
    )
    from pydeck.widget import DeckGLWidget  # pyright: ignore[reportMissingTypeStubs]

    # Leaflet Widget class is the same as a Widget
    # from ipyleaflet import Widget as LeafletWidget

from ._render_widget_base import ValueT, WidgetT, render_widget_base

__all__ = (
    "render_widget",
    "render_altair",
    "render_bokeh",
    "render_leaflet",
    "render_plotly",
    "render_pydeck",
)


class render_widget(render_widget_base[ValueT, Widget]):
    ...


class render_altair(render_widget_base[ValueT, JupyterChart]):
    ...


class render_bokeh(render_widget_base[ValueT, BokehModel]):
    ...


class render_leaflet(render_widget_base[WidgetT, WidgetT]):
    ...


class render_plotly(render_widget_base[ValueT, FigureWidget]):
    ...


class render_pydeck(render_widget_base[ValueT, DeckGLWidget]):
    ...
