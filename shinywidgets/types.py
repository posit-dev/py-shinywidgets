"""
Type aliases describing the values accepted by (and returned from)
shinywidgets render functions.

These aliases are primarily used as bounds on the renderers' value types, so
type checkers validate render functions against them automatically (no
annotation needed). They may also be used for annotations::

    from shinywidgets import render_plotly
    from shinywidgets.types import PlotlyFigure


    @render_plotly
    def plot() -> PlotlyFigure: ...

Note that annotating with a wide alias (e.g., `PlotlyValue`) widens the
inferred type of the output's ``.value`` attribute, so prefer a narrow
annotation (or none at all) and let inference do the work.

plotly is an optional dependency, so aliases that reference plotly types
are defined for type checkers under ``TYPE_CHECKING`` and resolved lazily at
runtime via module ``__getattr__`` (PEP 562): only users who access them --
and therefore have plotly installed -- pay for the import.
"""

import importlib
from typing import TYPE_CHECKING, Any, Dict, Tuple, Union

from ipywidgets import Widget

if TYPE_CHECKING:
    import plotly.graph_objects as go

__all__ = ("PlotlyConfig", "PlotlyFigure", "PlotlyValue")

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
    The full set of values accepted by a ``@render_plotly`` render function: a
    `PlotlyFigure`, optionally paired with a `PlotlyConfig` as a Dash-style
    ``(figure, config)`` tuple, or any ``ipywidgets.Widget`` (which
    ``as_widget()`` passes through unchanged).

    This alias is the bound on ``render_plotly``'s value type, so type
    checkers already validate render functions against it -- annotating with
    it is unnecessary, and widens the inferred type of the output's ``.value``.
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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
