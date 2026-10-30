"""Top-level package for shinywidgets."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version

__author__ = """Carson Sievert"""
__email__ = "carson@posit.co"
__version__: str

try:
    from .__version import __version__  # pyright: ignore[reportMissingImports]
except ImportError:
    try:
        __version__ = package_version("shinywidgets")
    except PackageNotFoundError:
        __version__ = "0+unknown"

from ._as_widget import as_widget
from ._bokeh import bokeh_dependency
from ._output_widget import output_widget
from ._render_widget import (
    render_altair,
    render_bokeh,
    render_bqplot,
    render_drawdata,
    render_embedding_atlas,
    render_geolibre,
    render_holoviews,
    render_ipyaladin,
    render_ipycanvas,
    render_ipycytoscape,
    render_ipydatagrid,
    render_ipyfilechooser,
    render_ipyleaflet,
    render_ipysigma,
    render_ipyvolume,
    render_itables,
    render_jscatter,
    render_k3d,
    render_keplergl,
    render_leafmap,
    render_lonboard,
    render_maplibre,
    render_matplotlib,
    render_mosaic_widget,
    render_nglview,
    render_niivue,
    render_obsplot,
    render_panel,
    render_perspective,
    render_plotly,
    render_plotnine,
    render_pydeck,
    render_pygwalker,
    render_pythreejs,
    render_quak,
    render_rerun,
    render_vitessce,
    render_vizarr,
    render_widget,
)
from ._shinywidgets import (
    reactive_read,
    register_widget,
    session_lifetime,
    shared_lifetime,
)

__all__ = (
    "__version__",
    # Render methods first
    "render_widget",
    "render_altair",
    "render_bokeh",
    "render_bqplot",
    "render_drawdata",
    "render_embedding_atlas",
    "render_geolibre",
    "render_holoviews",
    "render_ipyaladin",
    "render_ipycanvas",
    "render_ipycytoscape",
    "render_ipydatagrid",
    "render_ipyfilechooser",
    "render_ipyleaflet",
    "render_ipysigma",
    "render_ipyvolume",
    "render_itables",
    "render_jscatter",
    "render_k3d",
    "render_keplergl",
    "render_leafmap",
    "render_lonboard",
    "render_maplibre",
    "render_matplotlib",
    "render_nglview",
    "render_mosaic_widget",
    "render_niivue",
    "render_obsplot",
    "render_panel",
    "render_perspective",
    "render_plotly",
    "render_plotnine",
    "render_pydeck",
    "render_pygwalker",
    "render_pythreejs",
    "render_quak",
    "render_vizarr",
    "render_rerun",
    "render_vitessce",
    # Reactive read second
    "reactive_read",
    # UI methods third
    "output_widget",
    # Other methods last
    "as_widget",
    "bokeh_dependency",
    # Lifetime methods
    "session_lifetime",
    "shared_lifetime",
    # Soft deprecated
    "register_widget",
)
