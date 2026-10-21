from __future__ import annotations

import asyncio

import pytest
import shinywidgets
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny.session import session_context

pytest.importorskip("mosaic_widget")
from mosaic_widget import MosaicWidget  # noqa: E402

SPEC = {"plot": [{"mark": "dot", "data": {"from": "t"}, "x": "x", "y": "y"}]}


def test_render_mosaic_widget_is_exported() -> None:
    assert "render_mosaic_widget" in rw.__all__
    assert "render_mosaic_widget" in shinywidgets.__all__
    assert shinywidgets.render_mosaic_widget is rw.render_mosaic_widget


def test_render_mosaic_widget_is_render_widget_base() -> None:
    renderer = rw.render_mosaic_widget()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_mosaic_widget_fills_by_default(widget_session) -> None:
    r = rw.render_mosaic_widget()

    @r
    def _() -> MosaicWidget:
        return MosaicWidget(SPEC)

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert res["fill"] is True
    assert res["widget_pkg"] == "mosaic_widget"
    assert isinstance(r.widget, MosaicWidget)
    assert r.widget is r.value


def test_render_mosaic_widget_layout_height_disables_fill(widget_session) -> None:
    import ipywidgets as widgets

    r = rw.render_mosaic_widget()

    @r
    def _() -> MosaicWidget:
        return MosaicWidget(SPEC, layout=widgets.Layout(height="300px"))

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert res["fill"] is False
