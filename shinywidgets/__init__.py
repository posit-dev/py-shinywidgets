"""Top-level package for shinywidgets."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version

__author__ = """Carson Sievert"""
__email__ = "carson@posit.co"
try:
    from .__version import __version__
except ImportError:
    try:
        __version__ = package_version("shinywidgets")
    except PackageNotFoundError:
        __version__ = "0+unknown"
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
    "__version__",
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
