"""
Type aliases describing the values accepted by (and returned from) shinywidgets
render functions, for annotating render functions::

    from shinywidgets import render_plotly
    from shinywidgets.types import PlotlyValue


    @render_plotly
    def plot() -> PlotlyValue: ...

The corresponding packages (plotly, altair, bokeh, ...) are all optional
dependencies, so aliases that reference their types are defined for type
checkers under ``TYPE_CHECKING`` and resolved lazily at runtime via module
``__getattr__`` (PEP 562): only users who access an alias -- and therefore have
the package installed -- pay for the import.
"""

import importlib
from typing import TYPE_CHECKING, Any, Dict, Tuple, Union

if TYPE_CHECKING:
    import altair as alt
    import plotly.graph_objects as go
    from bokeh.models import LayoutDOM
    from holoviews.core.dimension import Dimensioned
    from maplibre.map import Map
    from panel.viewable import Viewable
    from pydeck import Deck

__all__ = (
    "AltairValue",
    "BokehValue",
    "HoloviewsValue",
    "MaplibreValue",
    "PanelValue",
    "PlotlyConfig",
    "PlotlyFigure",
    "PlotlyValue",
    "PydeckValue",
)

# The one alias that doesn't reference an optional dependency, so it's safe to
# define (and import) eagerly.
PlotlyConfig = Dict[str, Any]
"""
Plotly.js `config options <https://plotly.com/javascript/configuration-options/>`_,
as accepted by the ``(figure, config)`` tuple form of ``@render_plotly``.
"""

if TYPE_CHECKING:
    PlotlyFigure = Union[go.Figure, Tuple[go.Figure, PlotlyConfig]]
    """
    The supported return type of a ``@render_plotly`` render function: either a
    plotly figure, or a Dash-style ``(figure, config)`` tuple (see
    `PlotlyConfig`).
    """

    PlotlyValue = PlotlyFigure
    """Alias for `PlotlyFigure`, named consistently with the other ``*Value`` aliases."""

    AltairValue = Union[alt.TopLevelMixin, alt.JupyterChart]
    """
    The supported return type of a ``@render_altair`` render function: any
    altair top-level chart (``alt.Chart``, ``alt.LayerChart``, ...), or an
    already-coerced ``alt.JupyterChart``.
    """

    BokehValue = LayoutDOM
    """
    The supported return type of a ``@render_bokeh`` render function: any bokeh
    layout/model (e.g., a ``bokeh.plotting.figure``).
    """

    HoloviewsValue = Dimensioned
    """
    The supported return type of a ``@render_holoviews`` render function: a
    holoviews element or layout (hvplot outputs included).
    """

    MaplibreValue = Map
    """The supported return type of a ``@render_maplibre`` render function."""

    PanelValue = Viewable
    """The supported return type of a ``@render_panel`` render function."""

    PydeckValue = Deck
    """The supported return type of a ``@render_pydeck`` render function."""


def _require(alias: str, module: str) -> Any:
    try:
        return importlib.import_module(module)
    except ImportError:
        pkg = module.split(".")[0]
        raise ImportError(f"{alias} requires {pkg} (pip install {pkg}).") from None


def __getattr__(name: str) -> object:
    if name in ("PlotlyFigure", "PlotlyValue"):
        go = _require(name, "plotly.graph_objects")
        return Union[go.Figure, Tuple[go.Figure, PlotlyConfig]]
    if name == "AltairValue":
        alt = _require(name, "altair")
        return Union[alt.TopLevelMixin, alt.JupyterChart]
    if name == "BokehValue":
        return _require(name, "bokeh.models").LayoutDOM
    if name == "HoloviewsValue":
        return _require(name, "holoviews.core.dimension").Dimensioned
    if name == "MaplibreValue":
        return _require(name, "maplibre.map").Map
    if name == "PanelValue":
        return _require(name, "panel.viewable").Viewable
    if name == "PydeckValue":
        return _require(name, "pydeck").Deck
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
