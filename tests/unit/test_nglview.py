from __future__ import annotations

import asyncio
import importlib.util
import subprocess
import sys
import threading
import time
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


def test_constructor_height_opts_out_of_fill(
    nglview: ModuleType, widget_session: Session
) -> None:
    from shinywidgets._render_widget_base import set_layout_defaults

    with session_context(widget_session):
        filling = nglview.show_text(TINY_PDB, ext="pdb")
        fixed = nglview.NGLWidget(height="200px")

    assert set_layout_defaults(filling)[1] is True
    assert set_layout_defaults(fixed)[1] is False


def test_nglview_subclass_stops_its_threads(
    nglview: ModuleType, widget_session: Session
) -> None:
    # widget_pkg() of an app-defined subclass is the app's module, not
    # "nglview", but retirement must still stop its background threads
    class MyNGLWidget(nglview.NGLWidget):
        pass

    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            widget = MyNGLWidget()
        threads = remote_call_threads(widget)
        assert threads

        context.invalidate()

    for t in threads:
        t.join(timeout=2)
    assert not any(t.is_alive() for t in threads)


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


def test_direct_close_stops_nglview_threads(
    nglview: ModuleType, widget_session: Session
) -> None:
    # Closing the widget directly (rather than via render/session cleanup) must
    # stop its threads too: cleanup never revisits an already-closed widget
    with session_context(widget_session):
        widget = nglview.show_text(TINY_PDB, ext="pdb")
        threads = remote_call_threads(widget)
        assert threads

        widget.close()

    for t in threads:
        t.join(timeout=2)
    assert not any(t.is_alive() for t in threads)


def test_colormaker_registry_is_eagerly_shared(nglview: ModuleType) -> None:
    # The registry registers custom color schemes from its frontend view, so
    # every session must open it (see EAGERLY_SHARED_PACKAGES), and no render
    # or session may close it
    import shinywidgets._shinywidgets as sw

    registry = nglview.color.ColormakerRegistry
    assert sw.is_process_global(registry)
    assert "nglview" in sw.IMPORT_TIME_WIDGET_PACKAGES
    assert "nglview" in sw.EAGERLY_SHARED_PACKAGES
    assert not sw.is_swapped_out_default(registry)


def test_session_start_opens_colormaker_registry(
    nglview: ModuleType, widget_session: Session
) -> None:
    # Deliberately no shared_state fixture: the registry is a genuine
    # process-global singleton, and shared_state would close it (leaving it
    # comm-less) for later tests
    import shinywidgets._shinywidgets as sw

    registry = nglview.color.ColormakerRegistry
    with session_context(widget_session):
        # The first widget constructed in a session runs init_session(),
        # which eagerly opens the registry
        Widget()
    assert registry.model_id in sw.COMM_MANAGERS[widget_session.id].comms


def test_nglview_shutdown_releases_in_flight_acknowledgement_wait(
    nglview: ModuleType, widget_session: Session
) -> None:
    # A worker blocked in _wait_until_finished() (e.g. mid-loadFile) is waiting
    # on a browser acknowledgement that can't arrive once the comm is closed
    from shinywidgets._nglview import stop_nglview_threads

    with session_context(widget_session):
        widget = nglview.show_text(TINY_PDB, ext="pdb")
    released = threading.Event()

    def wait_for_acknowledgement() -> None:
        widget._wait_until_finished()
        released.set()

    waiter = threading.Thread(target=wait_for_acknowledgement, daemon=True)
    waiter.start()
    time.sleep(0.05)
    assert not released.is_set()

    stop_nglview_threads(widget)

    assert released.wait(timeout=2)
    waiter.join(timeout=2)
    assert not waiter.is_alive()


def test_nglview_shutdown_prevents_later_acknowledgement_waits(
    nglview: ModuleType, widget_session: Session
) -> None:
    # nglview's _wait_until_finished() clears the event before waiting, so a
    # worker that starts waiting *after* shutdown would block forever
    from shinywidgets._nglview import stop_nglview_threads

    with session_context(widget_session):
        widget = nglview.show_text(TINY_PDB, ext="pdb")
    stop_nglview_threads(widget)
    released = threading.Event()
    waiter = threading.Thread(
        target=lambda: (widget._wait_until_finished(), released.set()), daemon=True
    )
    waiter.start()

    assert released.wait(timeout=2)
    waiter.join(timeout=2)
    assert not waiter.is_alive()


def test_close_widget_ignores_non_viewer_nglview_widgets(
    nglview: ModuleType, widget_session: Session
) -> None:
    # Non-viewer nglview widgets (e.g. the global _ColormakerRegistry, or a
    # RepresentationControl) match a package-wide MRO check but have no
    # background threads (or `_event`); closing them must not raise.
    from nglview.color import _ColormakerRegistry
    from shinywidgets._shinywidgets import close_widget

    with session_context(widget_session):
        widget = _ColormakerRegistry()
    close_widget(widget)  # would raise AttributeError on w._event pre-fix
    assert widget.comm is not None


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
