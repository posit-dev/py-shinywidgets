from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from altair import JupyterChart  # pyright: ignore[reportMissingTypeStubs]
    from jupyter_bokeh import BokehModel  # pyright: ignore[reportMissingTypeStubs]
    from plotly.graph_objects import (  # pyright: ignore[reportMissingTypeStubs]
        FigureWidget,
    )
    from pydeck.widget import DeckGLWidget  # pyright: ignore[reportMissingTypeStubs]
else:
    JupyterChart = BokehModel = FigureWidget = DeckGLWidget = object

from ._render_widget_base import ValueT, WidgetT, render_widget_base

__all__ = (
    "render_widget",
    "render_altair",
    "render_bokeh",
    "render_plotly",
    "render_pydeck",
)

# In the generic case, just relay whatever the user's return type is
# since we're not doing any coercion
class render_widget(render_widget_base[WidgetT, WidgetT]):
    ...

# Package specific renderers that require coercion (via as_widget())
# NOTE: the types on these classes should mirror what as_widget() does
class render_altair(render_widget_base[ValueT, JupyterChart]):
    ...

class render_bokeh(render_widget_base[ValueT, BokehModel]):
    ...

class render_plotly(render_widget_base[ValueT, FigureWidget]):
    ...

class render_pydeck(render_widget_base[ValueT, DeckGLWidget]):
    ...
