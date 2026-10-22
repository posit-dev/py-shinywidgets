from __future__ import annotations

import asyncio
import sys
import warnings
from typing import TYPE_CHECKING, cast

import matplotlib.pyplot as plt
import pandas as pd
import pytest
import shinywidgets._render_widget as rw
from matplotlib.figure import Figure
from plotnine import aes, geom_point, ggplot, theme
from shiny import Session
from shiny.reactive import Context
from shiny.session import session_context
from shinywidgets import as_widget
from shinywidgets._as_widget import as_widget_plotnine
from shinywidgets._render_widget_base import WidgetRenderContext

if TYPE_CHECKING:
    from ipympl.backend_nbagg import Canvas


def test_ggplot_coerced_to_ipympl_canvas(widget_session: Session) -> None:
    with session_context(widget_session):
        canvas = cast("Canvas", as_widget(scatter()))

    assert type(canvas).__name__ == "Canvas"
    # The canvas holds the drawn plot: plotnine attaches its layout engine,
    # which re-lays out the plot whenever the figure is resized and redrawn
    engine = canvas.figure.get_layout_engine()
    assert type(engine).__name__ == "PlotnineLayoutEngine"
    assert len(canvas.figure.axes) == 1


def test_composition_coerced_to_ipympl_canvas(widget_session: Session) -> None:
    with session_context(widget_session):
        canvas = cast("Canvas", as_widget(scatter() | scatter()))

    assert len(canvas.figure.axes) == 2


def test_figure_size_is_drawn_figure_size(widget_session: Session) -> None:
    with session_context(widget_session):
        canvas = cast("Canvas", as_widget(scatter() + theme(figure_size=(4, 2))))

    assert tuple(canvas.figure.get_size_inches()) == (4, 2)


def test_users_plot_is_not_mutated(widget_session: Session) -> None:
    plot = scatter()
    with session_context(widget_session):
        first = cast("Canvas", as_widget(plot))
        second = cast("Canvas", as_widget(plot))

    # ggplot.draw() attaches the figure to the plot, and a later draw() reuses
    # it, so the same plot object must yield independent figures
    assert not hasattr(plot, "figure")
    assert first.figure is not second.figure
    assert len(second.figure.axes) == 1


def test_already_drawn_plot_gets_its_own_figure(widget_session: Session) -> None:
    plot = scatter()
    with session_context(widget_session):
        drawn = plot.draw()
        first = cast("Canvas", as_widget(plot))
        second = cast("Canvas", as_widget(plot + theme(figure_size=(4, 2))))

    # ggplot's deepcopy keeps the figure a draw() attached, so copies of a drawn
    # plot would all draw onto (and share a canvas with) that one figure
    assert len({id(drawn), id(first.figure), id(second.figure)}) == 3
    assert len(first.figure.axes) == len(second.figure.axes) == 1
    assert plot.figure is drawn


def test_already_drawn_composition_gets_its_own_figure(
    widget_session: Session,
) -> None:
    composition = (scatter() | scatter()) / scatter()
    with session_context(widget_session):
        drawn = composition.draw()
        canvas = cast("Canvas", as_widget(composition))

    assert canvas.figure is not drawn
    assert len(canvas.figure.axes) == len(drawn.axes) == 3
    assert composition.figure is drawn


def test_users_composition_is_not_mutated(widget_session: Session) -> None:
    left, right = scatter(), scatter()
    composition = left | right
    with session_context(widget_session):
        first = cast("Canvas", as_widget(composition))
        second = cast("Canvas", as_widget(composition))

    assert not any(hasattr(p, "figure") for p in (composition, left, right))
    assert first.figure is not second.figure
    assert len(second.figure.axes) == 2


def test_header_and_footer_hidden(widget_session: Session) -> None:
    with session_context(widget_session):
        canvas = cast("Canvas", as_widget(scatter()))

    assert canvas.header_visible is False
    assert canvas.footer_visible is False


def test_no_pyplot_figures_leak_across_renders(widget_session: Session) -> None:
    before = set(plt.get_fignums())
    with session_context(widget_session), warnings.catch_warnings():
        # e.g., "More than 20 figures have been opened"
        warnings.simplefilter("error", RuntimeWarning)
        for _ in range(25):
            context = Context()
            with context(), WidgetRenderContext():
                as_widget(scatter())
            context.invalidate()

    assert set(plt.get_fignums()) == before


def test_rejects_non_plot() -> None:
    with pytest.raises(TypeError, match="plotnine"):
        as_widget_plotnine(geom_point())


def test_missing_ipympl_error_mentions_plotnine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "ipympl.backend_nbagg", None)
    with pytest.raises(
        ImportError,
        match=r"Install the ipympl package to use plotnine with shinywidgets \(pip install ipympl\)",
    ):
        as_widget(FakePlot())


@pytest.mark.parametrize(
    "renderer", [rw.render_plotnine, rw.render_matplotlib, rw.render_widget]
)
def test_renderers_accept_ggplot(renderer: type, widget_session: Session) -> None:
    r = renderer()

    @r
    def _():  # noqa: ANN202
        return scatter()

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert res["widget_pkg"] == "ipympl"
    assert res["fill"] is True
    assert type(r.widget).__name__ == "Canvas"
    assert isinstance(r.value, ggplot)


def scatter() -> ggplot:
    df = pd.DataFrame({"x": [1, 2, 3], "y": [3, 1, 2]})
    return ggplot(df, aes("x", "y")) + geom_point()


# Draws a figure outside of pyplot (whose backend may be ipympl, depending on
# what ran earlier in the process, which would construct a widget on draw)
class FakePlot:
    __module__ = "plotnine.ggplot"

    def draw(self, *, show: bool = False) -> Figure:
        return Figure()
