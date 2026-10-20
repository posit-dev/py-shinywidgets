"""
Type aliases describing the values accepted by (and returned from) shinywidgets
render functions, for annotating render functions::

    from shinywidgets import render_plotly
    from shinywidgets.types import PlotlyValue


    @render_plotly
    def plot() -> PlotlyValue: ...

Every ``*Value`` alias also includes ``ipywidgets.Widget``, since
:func:`~shinywidgets.as_widget` passes any widget through unchanged -- so a
render function may always return a pre-built widget (e.g., the widget class
the renderer would have coerced to) instead of the package-specific object.

The corresponding packages (plotly, altair, bokeh, ...) are all optional
dependencies, so aliases that reference their types are defined for type
checkers under ``TYPE_CHECKING`` and resolved lazily at runtime via module
``__getattr__`` (PEP 562): only users who access an alias -- and therefore have
the package installed -- pay for the import.
"""

import importlib
from typing import TYPE_CHECKING, Any, Dict, Tuple, Union

from ipywidgets import Widget

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
    PlotlyFigure = Union[go.Figure, go.FigureWidget]
    """
    A plotly figure: either a plain ``go.Figure`` (coerced to a
    ``go.FigureWidget`` on render) or a pre-built ``go.FigureWidget``. (The
    two are sibling classes, not subclasses of one another, so both are
    listed.)
    """

    PlotlyValue = Union[PlotlyFigure, Tuple[PlotlyFigure, PlotlyConfig], Widget]
    """
    The supported return type of a ``@render_plotly`` render function: a
    `PlotlyFigure`, optionally paired with a `PlotlyConfig` as a Dash-style
    ``(figure, config)`` tuple, or any ``ipywidgets.Widget``.
    """

    AltairValue = Union[alt.TopLevelMixin, Widget]
    """
    The supported return type of a ``@render_altair`` render function: any
    altair top-level chart (``alt.Chart``, ``alt.LayerChart``, ...), or any
    ``ipywidgets.Widget`` (e.g., an already-coerced ``alt.JupyterChart``).
    """

    BokehValue = Union[LayoutDOM, Widget]
    """
    The supported return type of a ``@render_bokeh`` render function: any bokeh
    layout/model (e.g., a ``bokeh.plotting.figure``), or any
    ``ipywidgets.Widget`` (e.g., an already-coerced ``jupyter_bokeh.BokehModel``).
    """

    HoloviewsValue = Union[Dimensioned, Widget]
    """
    The supported return type of a ``@render_holoviews`` render function: a
    holoviews element or layout (hvplot outputs included), or any
    ``ipywidgets.Widget``.
    """

    MaplibreValue = Union[Map, Widget]
    """
    The supported return type of a ``@render_maplibre`` render function: a
    ``maplibre.Map``, or any ``ipywidgets.Widget`` (e.g., an already-coerced
    ``maplibre.ipywidget.MapWidget``).
    """

    PanelValue = Union[Viewable, Widget]
    """
    The supported return type of a ``@render_panel`` render function: a panel
    pane or viewable, or any ``ipywidgets.Widget``.
    """

    PydeckValue = Union[Deck, Widget]
    """
    The supported return type of a ``@render_pydeck`` render function: a
    ``pydeck.Deck``, or any ``ipywidgets.Widget`` (e.g., an already-coerced
    ``pydeck.widget.DeckGLWidget``).
    """


def _require(alias: str, module: str) -> Any:
    try:
        return importlib.import_module(module)
    except ImportError:
        pkg = module.split(".")[0]
        raise ImportError(f"{alias} requires {pkg} (pip install {pkg}).") from None


def __getattr__(name: str) -> object:
    if name == "PlotlyFigure":
        go = _require(name, "plotly.graph_objects")
        return Union[go.Figure, go.FigureWidget]
    if name == "PlotlyValue":
        go = _require(name, "plotly.graph_objects")
        figure = Union[go.Figure, go.FigureWidget]
        return Union[figure, Tuple[figure, PlotlyConfig], Widget]
    if name == "AltairValue":
        return Union[_require(name, "altair").TopLevelMixin, Widget]
    if name == "BokehValue":
        return Union[_require(name, "bokeh.models").LayoutDOM, Widget]
    if name == "HoloviewsValue":
        return Union[_require(name, "holoviews.core.dimension").Dimensioned, Widget]
    if name == "MaplibreValue":
        return Union[_require(name, "maplibre.map").Map, Widget]
    if name == "PanelValue":
        return Union[_require(name, "panel.viewable").Viewable, Widget]
    if name == "PydeckValue":
        return Union[_require(name, "pydeck").Deck, Widget]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
