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
from shinywidgets._config import _SETTINGS
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


def test_as_widget_rejects_per_point_string_colors(widget_session: Session) -> None:
    ipv = pytest.importorskip("ipyvolume")

    with session_context(widget_session):
        fig = ipv.figure()
        scatter = ipv.scatter(
            [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], color=["tomato", "seagreen"]
        )
        with pytest.raises(TypeError, match=r"Scatter\.color.*array of strings"):
            as_widget(fig)
        # The invalid value is sanitized away: a string array left in place
        # would hang the next flush in ipyvolume's serializer
        assert scatter.color is None


def test_as_widget_rejects_string_colors_from_the_quickscatter_container(
    widget_session: Session,
) -> None:
    ipv = pytest.importorskip("ipyvolume")

    with session_context(widget_session):
        container = ipv.quickscatter(
            [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], color=["tomato", "seagreen"]
        )
        with pytest.raises(TypeError, match=r"Scatter\.color.*array of strings"):
            as_widget(container)
        assert container.figure.scatters[0].color is None


def test_as_widget_rejects_string_color_selected(widget_session: Session) -> None:
    ipv = pytest.importorskip("ipyvolume")

    with session_context(widget_session):
        fig = ipv.figure()
        scatter = ipv.scatter([0.0, 1.0], [0.0, 1.0], [0.0, 1.0])
        scatter.color_selected = ["tomato", "seagreen"]
        with pytest.raises(
            TypeError, match=r"Scatter\.color_selected.*array of strings"
        ):
            as_widget(fig)
        assert scatter.color_selected is None


def test_as_widget_rejects_mesh_string_colors(widget_session: Session) -> None:
    ipv = pytest.importorskip("ipyvolume")
    import numpy as np

    with session_context(widget_session):
        mesh = ipv.widgets.Mesh(
            x=np.zeros((2, 2)), y=np.zeros((2, 2)), z=np.zeros((2, 2)), color="red"
        )
        mesh.color = ["tomato", "seagreen"]
        fig = ipv.Figure(meshes=[mesh])
        with pytest.raises(TypeError, match=r"Mesh\.color.*array of strings"):
            as_widget(fig)
        assert mesh.color is None


def test_flush_after_string_color_rejection_does_not_hang() -> None:
    pytest.importorskip("ipyvolume")

    # The coercion error must sanitize the invalid trait: the scatter's
    # deferred comm open still runs at the next flush (nothing closes widgets
    # created during a failed render) and would infinite-loop in ipyvolume's
    # serializer on a leftover string array. Run out-of-process so a
    # regression fails here instead of hanging the test suite.
    code = """
import asyncio

import shinywidgets._shinywidgets as sw
import ipyvolume as ipv
from shiny import App, reactive, ui
from shiny._connection import MockConnection
from shiny.reactive._reactives import Context
from shiny.session import session_context
from shinywidgets import render_ipyvolume


async def main():
    app = App(ui.page_fluid(), lambda input, output, session: None)
    session = app._create_session(MockConnection())
    sw.SHINYWIDGETS_CDN_ONLY = True

    r = render_ipyvolume()

    @r
    def bad():
        ipv.scatter(
            [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], color=["tomato", "seagreen"]
        )
        return ipv.gcf()

    with session_context(session):
        ctx = Context()
        with ctx():
            try:
                await r.render()
            except TypeError:
                pass
        await reactive.flush()
    print("FLUSH OK", flush=True)


asyncio.run(main())
"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            "The flush after a rejected string color array hung -- the "
            "rejected widget's deferred comm open serialized the invalid value"
        )
    assert "FLUSH OK" in proc.stdout, proc.stderr


def test_as_widget_accepts_a_scalar_string_color(widget_session: Session) -> None:
    ipv = pytest.importorskip("ipyvolume")

    with session_context(widget_session):
        fig = ipv.figure()
        ipv.scatter([0.0, 1.0], [0.0, 1.0], [0.0, 1.0], color="tomato")
        assert as_widget(fig) is fig


def test_as_widget_accepts_numeric_per_point_colors(widget_session: Session) -> None:
    ipv = pytest.importorskip("ipyvolume")
    import numpy as np

    with session_context(widget_session):
        fig = ipv.figure()
        ipv.scatter(
            [0.0, 1.0],
            [0.0, 1.0],
            [0.0, 1.0],
            color=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        )
        assert as_widget(fig) is fig


def test_vuetify_widget_open_serves_jupyter_vue(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The quickscatter() Container is a jupyter-vuetify widget, whose AMD
    # bundle externally requires('jupyter-vue'); its comm open must carry a
    # require.js path config for jupyter-vue or the browser 404s requesting
    # jupyter-vue.js at the app root (then falls back to a CDN). The mapping
    # is only served in local-dependency mode, so disable the fixture's
    # CDN-only mode for this test.
    monkeypatch.setitem(_SETTINGS, "cdn_only", False)
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
