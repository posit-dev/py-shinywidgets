from __future__ import annotations

import asyncio

import pytest
import shinywidgets
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny.session import session_context

ipyniivue = pytest.importorskip("ipyniivue", reason="ipyniivue isn't installed")

from ipyniivue import NiiVue


def render_one(renderer: rwb.render_widget_base, value: object) -> dict[str, object]:

    @renderer
    def _():  # noqa: ANN202
        return value

    return asyncio.run(renderer._render())  # type: ignore


def test_render_niivue_is_render_widget_base() -> None:
    assert isinstance(rw.render_niivue(), rwb.render_widget_base)


def test_render_niivue_is_exported() -> None:
    assert "render_niivue" in rw.__all__
    assert "render_niivue" in shinywidgets.__all__


def test_render_niivue_passes_widget_through(widget_session) -> None:
    r = rw.render_niivue()
    with session_context(widget_session):
        nv = NiiVue()
        res = render_one(r, nv)

    assert res is not None
    assert r.widget is nv
    assert res["widget_pkg"] == "ipyniivue"
    # NiiVue's `height` option (default 300) isn't an ipywidgets Layout height,
    # so the output fills its container (and the canvas tracks it)
    assert res["fill"] is True
