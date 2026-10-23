import asyncio

import pytest
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny.session import session_context
from shinywidgets import as_widget

bqplot = pytest.importorskip("bqplot")
bplt = pytest.importorskip("bqplot.pyplot")


def test_as_widget_passes_figure_through(widget_session) -> None:
    with session_context(widget_session):
        fig = bqplot.Figure()
        assert as_widget(fig) is fig


def test_render_bqplot_renders_pyplot_figure(widget_session) -> None:
    r = rw.render_bqplot()

    @r
    def _():  # noqa: ANN202
        bplt.figure()
        bplt.scatter([1, 2, 3], [3, 1, 2])
        return bplt.current_figure()

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert res is not None
    assert isinstance(r.widget, bqplot.Figure)
    assert r.widget is r.value
    assert isinstance(r.widget.marks[0], bqplot.Scatter)


def test_figure_fills_by_default(widget_session) -> None:
    with session_context(widget_session):
        _, fill = rwb.set_layout_defaults(bqplot.Figure())
    assert fill is True


def test_figure_layout_height_disables_fill(widget_session) -> None:
    with session_context(widget_session):
        fig = bqplot.Figure(layout={"height": "300px"})
        _, fill = rwb.set_layout_defaults(fig)
    assert fill is False
