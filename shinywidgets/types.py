"""
Type aliases describing the values accepted by (and returned from) shinywidgets
render functions, for annotating render functions::

    from shinywidgets import render_plotly
    from shinywidgets.types import PlotlyFigure


    @render_plotly
    def plot() -> PlotlyFigure: ...

plotly is an optional dependency, so aliases that reference plotly types
(`PlotlyFigure`) are defined for type checkers under ``TYPE_CHECKING`` and
resolved lazily at runtime via module ``__getattr__`` (PEP 562): only users who
access them -- and therefore have plotly installed -- pay for the import.
"""

from typing import TYPE_CHECKING, Any, Dict, Tuple, Union

if TYPE_CHECKING:
    import plotly.graph_objects as go

__all__ = ("PlotlyConfig", "PlotlyFigure")

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


def __getattr__(name: str) -> object:
    if name == "PlotlyFigure":
        try:
            import plotly.graph_objects as go
        except ImportError:
            raise ImportError(
                "PlotlyFigure requires plotly (pip install plotly)."
            ) from None
        return Union[go.Figure, Tuple[go.Figure, PlotlyConfig]]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
