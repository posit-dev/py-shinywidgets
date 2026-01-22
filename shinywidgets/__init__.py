"""Top-level package for shinywidgets."""

__author__ = """Carson Sievert"""
__email__ = "carson@posit.co"
__version__ = "0.7.0"

from ._as_widget import as_widget
from ._dependencies import bokeh_dependency
from ._output_widget import output_widget
from ._render_widget import (
    render_altair,
    render_bokeh,
    render_plotly,
    render_pydeck,
    render_widget,
)
from ._shinywidgets import reactive_read, register_widget

__all__ = (
    # Render methods first
    "render_widget",
    "render_altair",
    "render_bokeh",
    "render_plotly",
    "render_pydeck",
    # Reactive read second
    "reactive_read",
    # UI methods third
    "output_widget",
    # Other methods last
    "as_widget",
    "bokeh_dependency",
    # Soft deprecated
    "register_widget",
)
