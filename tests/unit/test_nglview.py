from __future__ import annotations

import asyncio
import importlib.util
import subprocess
import sys
import threading
from types import ModuleType

import pytest
import shinywidgets
import shinywidgets._render_widget as rw
from ipywidgets import Widget
from shiny import Session
from shiny.reactive import Context
from shiny.session import session_context
from shinywidgets._render_widget_base import WidgetRenderContext

TINY_PDB = (
    "ATOM      1  N   ALA A   1      11.104   6.134  -6.504  1.00  0.00           N\n"
    "ATOM      2  CA  ALA A   1      11.639   6.071  -5.147  1.00  0.00           C\n"
    "END\n"
)


@pytest.fixture(scope="module")
def nglview() -> ModuleType:
    return pytest.importorskip("nglview")


@pytest.mark.skipif(
    importlib.util.find_spec("nglview") is None, reason="nglview not installed"
)
def test_nglview_can_be_imported_after_shinywidgets() -> None:
    # nglview constructs a (global) widget at import time, outside any session
    result = subprocess.run(
        [sys.executable, "-c", "import shinywidgets; import nglview"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_render_nglview_is_exported() -> None:
    assert shinywidgets.render_nglview is rw.render_nglview
    assert "render_nglview" in shinywidgets.__all__


def test_render_nglview_renders_widget_that_fills(
    nglview: ModuleType, widget_session: Session
) -> None:
    r = rw.render_nglview()

    @r
    def _():  # noqa: ANN202
        return nglview.show_text(TINY_PDB, ext="pdb")

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert res["widget_pkg"] == "nglview"
    assert res["fill"] is True
    assert isinstance(r.widget, nglview.NGLWidget)


def remote_call_threads(widget: Widget) -> list[threading.Thread]:
    from nglview.remote_thread import RemoteCallThread

    return [
        t
        for t in threading.enumerate()
        if isinstance(t, RemoteCallThread) and t.view is widget
    ]


def test_retired_nglview_widget_stops_its_threads(
    nglview: ModuleType, widget_session: Session
) -> None:
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            widget = nglview.show_text(TINY_PDB, ext="pdb")
        threads = remote_call_threads(widget)
        assert threads

        # Retiring the render closes the widget, which must also end the
        # threads nglview polls (and keeps the widget alive) from
        context.invalidate()

    for t in threads:
        t.join(timeout=2)
    assert not any(t.is_alive() for t in threads)


def test_session_end_stops_nglview_threads(
    nglview: ModuleType, widget_session: Session
) -> None:
    with session_context(widget_session):
        widget = nglview.show_text(TINY_PDB, ext="pdb")
    threads = remote_call_threads(widget)
    assert threads

    asyncio.run(widget_session.close())

    for t in threads:
        t.join(timeout=2)
    assert not any(t.is_alive() for t in threads)
