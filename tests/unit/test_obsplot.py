from __future__ import annotations

import asyncio

import ipywidgets as widgets
import pytest
import shinywidgets
import shinywidgets._render_widget as rw
from shiny.session import session_context
from shinywidgets._as_widget import as_widget

pytest.importorskip("pyobsplot")
from pyobsplot import Plot  # noqa: E402
from pyobsplot.widget import ObsplotWidget  # noqa: E402

SPEC = {"marks": [Plot.ruleY([0])]}


def test_render_obsplot_is_exported() -> None:
    assert "render_obsplot" in rw.__all__
    assert "render_obsplot" in shinywidgets.__all__
    assert shinywidgets.render_obsplot is rw.render_obsplot


def test_render_obsplot_fills_by_default(widget_session) -> None:
    r = rw.render_obsplot()

    @r
    def _() -> ObsplotWidget:
        return Plot.plot(SPEC)

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert res["fill"] is True
    assert res["widget_pkg"] == "pyobsplot"
    assert isinstance(r.widget, ObsplotWidget)
    assert r.widget is r.value


def test_render_obsplot_layout_height_disables_fill(widget_session) -> None:
    r = rw.render_obsplot()

    @r
    def _() -> ObsplotWidget:
        w = Plot.plot(SPEC)
        w.layout = widgets.Layout(height="300px")
        return w

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert res["fill"] is False


def test_as_widget_rejects_plot_creator() -> None:
    from pyobsplot import Obsplot

    with pytest.raises(TypeError, match="plot creator"):
        as_widget(Obsplot())


def test_render_obsplot_rejects_plot_creator(widget_session) -> None:
    r = rw.render_obsplot()

    @r
    def _() -> ObsplotWidget:
        return Plot  # type: ignore

    with session_context(widget_session):
        with pytest.raises(TypeError, match="plot creator"):
            asyncio.run(r._render())
