from __future__ import annotations

import asyncio

import pytest
import shinywidgets
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny.session import session_context

vitessce = pytest.importorskip("vitessce", reason="vitessce isn't installed")

from vitessce import VitessceConfig
from vitessce.widget import VitessceWidget


def render_one(renderer: rwb.render_widget_base, value: object) -> dict[str, object]:

    @renderer
    def _():  # noqa: ANN202
        return value

    return asyncio.run(renderer._render())  # type: ignore


def make_config() -> VitessceConfig:
    return VitessceConfig(schema_version="1.0.15", name="test")


def test_render_vitessce_is_render_widget_base() -> None:
    assert isinstance(rw.render_vitessce(), rwb.render_widget_base)


def test_render_vitessce_is_exported() -> None:
    assert "render_vitessce" in rw.__all__
    assert "render_vitessce" in shinywidgets.__all__


def test_render_vitessce_passes_widget_through(widget_session) -> None:
    r = rw.render_vitessce()
    with session_context(widget_session):
        widget = make_config().widget()
        res = render_one(r, widget)

    assert res is not None
    assert r.widget is widget
    assert res["widget_pkg"] == "vitessce"


def test_render_vitessce_coerces_config(widget_session) -> None:
    r = rw.render_vitessce()
    with session_context(widget_session):
        config = make_config()
        res = render_one(r, config)

    assert res is not None
    # The config's .widget() was called for us
    assert isinstance(r.widget, VitessceWidget)
    assert r.value is config
    assert res["widget_pkg"] == "vitessce"


def test_render_vitessce_rejects_unsupported_value(widget_session) -> None:
    r = rw.render_vitessce()
    with (
        session_context(widget_session),
        pytest.raises(TypeError, match="VitessceWidget"),
    ):
        render_one(r, object())
