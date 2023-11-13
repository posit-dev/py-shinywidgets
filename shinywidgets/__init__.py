"""Top-level package for shinywidgets."""

__author__ = """Carson Sievert"""
__email__ = "carson@rstudio.com"
__version__ = "0.2.3"

from ._dependencies import bokeh_dependency
from ._shinywidgets import (
    as_widget,
    output_widget,
    reactive_read,
    register_widget,
    render_widget,
)

__all__ = ("output_widget", "register_widget", "render_widget", "reactive_read", "bokeh_dependency", "as_widget")
