from __future__ import annotations

import asyncio
import json
import subprocess
import sys

import pytest
from shiny import Session, reactive
from shiny.session import session_context
from shinywidgets import render_ipyvolume
from shinywidgets._as_widget import as_widget
from shinywidgets._render_widget_base import render_widget_base


def test_render_ipyvolume_is_render_widget_base() -> None:
    renderer = render_ipyvolume()
    assert isinstance(renderer, render_widget_base)


def test_import_ipyvolume_after_shinywidgets() -> None:
    # ipyvue (which ipyvolume imports via ipyvuetify) constructs a module-level
    # widget at import time, so importing ipyvolume at the top of an app module
    # (i.e., outside a session) must not error
    code = "import shinywidgets, ipyvolume; print(ipyvolume.__version__)"
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr


def test_as_widget_passes_a_figure_through(widget_session: Session) -> None:
    ipv = pytest.importorskip("ipyvolume")

    with session_context(widget_session):
        fig = ipv.figure()
        assert as_widget(fig) is fig
        assert render_ipyvolume()._as_widget(fig) is fig


def test_as_widget_unwraps_the_quickscatter_container(widget_session: Session) -> None:
    ipv = pytest.importorskip("ipyvolume")

    with session_context(widget_session):
        # The idiomatic pylab workflow: quickscatter() draws into a new current
        # figure and returns the current container (figure + control widgets)
        container = ipv.quickscatter([0.0, 1.0], [0.0, 1.0], [0.0, 1.0])
        fig = ipv.gcf()
        assert as_widget(container) is fig
        assert render_ipyvolume()._as_widget(container) is fig


def test_as_widget_errors_helpfully_for_a_bare_scene_object(
    widget_session: Session,
) -> None:
    ipv = pytest.importorskip("ipyvolume")

    with session_context(widget_session):
        ipv.figure()
        scatter = ipv.scatter([0.0], [0.0], [0.0])
        with pytest.raises(TypeError, match="ipyvolume"):
            as_widget(scatter)


def test_vuetify_widget_open_serves_jupyter_vue(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The quickscatter() Container is a jupyter-vuetify widget, whose AMD
    # bundle externally requires('jupyter-vue'); its comm open must carry a
    # require.js path config for jupyter-vue or the browser 404s requesting
    # jupyter-vue.js at the app root (then falls back to a CDN)
    ipv = pytest.importorskip("ipyvolume")

    messages: list[dict] = []

    async def send_custom_message(type: str, message: object) -> None:
        if type == "shinywidgets_comm_open":
            assert isinstance(message, str)
            messages.append(json.loads(message))

    monkeypatch.setattr(widget_session, "send_custom_message", send_custom_message)

    with session_context(widget_session):
        container = ipv.quickscatter([0.0, 1.0], [0.0, 1.0], [0.0, 1.0])
        asyncio.get_event_loop().run_until_complete(reactive.flush())
        asyncio.get_event_loop().run_until_complete(
            widget_session._flush_callbacks.invoke()
        )

    assert container._model_module == "jupyter-vuetify"
    msg = next(m for m in messages if m["content"]["comm_id"] == container.model_id)
    dep_names = [d["name"] for d in msg["content"]["html_deps"]]
    assert "jupyter-vue" in dep_names
