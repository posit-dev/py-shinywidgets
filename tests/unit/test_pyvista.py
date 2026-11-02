import asyncio
import sys
import threading
from collections.abc import Coroutine, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

import pytest
from ipywidgets import HTML, Widget

pv = pytest.importorskip("pyvista")
pytest.importorskip("trame_pyvista")

pv.OFF_SCREEN = True

import shinywidgets._shinywidgets as sw  # noqa: E402
from shiny import App, Session, ui  # noqa: E402
from shiny._connection import MockConnection  # noqa: E402
from shiny.session import session_context  # noqa: E402
from shinywidgets._as_widget import (  # noqa: E402
    _isolated_trame_cli_args,
    as_widget,
    as_widget_pyvista,
    ensure_pyvista_trame_server,
)
from shinywidgets._render_widget_base import (  # noqa: E402
    pyvista_layout_defaults,
    set_layout_defaults,
)

from tests.unit.conftest import widget_test_server  # noqa: E402

T = TypeVar("T")


def run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def other_session() -> Iterator[Session]:
    session = App(ui.page_fluid(), widget_test_server)._create_session(MockConnection())
    try:
        yield session
    finally:
        run(session.close())


@pytest.fixture
def fresh_viewer_page(shared_state: None) -> Iterator[None]:
    """
    Give this test its own trame-pyvista viewer page.

    `trame_pyvista.jupyter._get_viewer_page()` caches one `_ViewerPage` per
    process (recreating it only once the cached one is closed), so tests that
    construct one would otherwise share -- and interfere with -- whichever
    instance an earlier test left behind.
    """
    import trame_pyvista.jupyter as tpj

    tpj._shared_viewer_page = None
    try:
        yield
    finally:
        tpj._shared_viewer_page = None


def coerce_plotter(widget_session, pl: "pv.Plotter") -> Widget:
    with session_context(widget_session):
        return as_widget_pyvista(pl)


def make_plotter() -> "pv.Plotter":
    pl = pv.Plotter(notebook=True, window_size=[400, 300])
    pl.add_mesh(pv.Sphere())
    return pl


def test_ensure_pyvista_trame_server_starts_for_concurrent_callers() -> None:
    # First render(s) may race to start the shared trame server: every caller
    # should unblock once it's ready, without erroring or deadlocking (this
    # test runs first, while the server is still cold)
    barrier = threading.Barrier(8)

    def call_ensure() -> None:
        barrier.wait(timeout=10)
        ensure_pyvista_trame_server()

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(call_ensure) for _ in range(8)]
        for f in futures:
            f.result(timeout=60)

    from trame_pyvista.widgets import get_server

    server = get_server(pv.global_theme.trame.jupyter_server_name)
    assert server.running


def test_ensure_pyvista_trame_server_idempotent() -> None:
    ensure_pyvista_trame_server()
    # Fast path: the server is already running, so this returns immediately
    ensure_pyvista_trame_server()


def test_trame_cli_args_isolated_from_process_argv(monkeypatch) -> None:
    # `shiny run app.py --host 0.0.0.0` must not leak into trame's CLI
    # parsing: trame only honors its host= keyword when the parsed host is
    # the default 'localhost', so the process's --host would otherwise bind
    # the internal export server to 0.0.0.0 as well (outside Shiny's auth).
    # trame skips sys.argv parsing when pytest is loaded, so drop that guard
    # to exercise the real parsing path.
    from trame_server.core import Server

    monkeypatch.setattr(sys, "argv", ["shiny", "run", "app.py", "--host", "0.0.0.0"])
    monkeypatch.delitem(sys.modules, "pytest", raising=False)
    server = Server()
    # Without the isolation, trame's parser picks up the process's --host
    assert server.cli.parse_known_args()[0].host == "0.0.0.0"
    with _isolated_trame_cli_args():
        assert server.cli.parse_known_args()[0].host == "localhost"


def test_ensure_pyvista_trame_server_retries_failed_start(monkeypatch) -> None:
    # A synchronous startup failure must not be cached: the next render
    # retries with a fresh attempt (under a distinct server name, so this
    # doesn't disturb the shared server other tests use)
    import shinywidgets._as_widget as aw
    from trame_pyvista.widgets import get_server

    monkeypatch.setattr(
        pv.global_theme.trame, "jupyter_server_name", "pyvista-jupyter-retry"
    )

    def failing_start(self, server) -> None:
        raise OSError("transient startup failure")

    original_start = aw._PyvistaTrameServerStartup.start
    monkeypatch.setattr(aw._PyvistaTrameServerStartup, "start", failing_start)
    with pytest.raises(OSError, match="transient"):
        ensure_pyvista_trame_server()
    # The failed attempt wasn't cached, so a retry starts cleanly
    monkeypatch.setattr(aw._PyvistaTrameServerStartup, "start", original_start)
    ensure_pyvista_trame_server()
    assert get_server("pyvista-jupyter-retry").running


def test_as_widget_pyvista_coerces_plotter(widget_session) -> None:
    pl = make_plotter()
    w = coerce_plotter(widget_session, pl)
    assert isinstance(w, HTML)
    assert 'class="pyvista"' in w.value
    # The scene is embedded, client-side (no separate trame server)
    assert "srcdoc=" in w.value
    assert "http://localhost" not in w.value
    # Fill sizing: the iframe and widget layout stretch to the container
    assert "width: 100%" in w.value
    assert "height: 100%" in w.value
    assert w.layout.width == "100%"
    assert w.layout.height == "100%"
    # The plotter's GL resources are released after the scene is exported
    assert pl._closed


def test_as_widget_coerces_plotter_via_package_map(widget_session) -> None:
    with session_context(widget_session):
        w = as_widget(make_plotter())
    assert isinstance(w, HTML)
    assert 'class="pyvista"' in w.value


def test_as_widget_coerces_plotter_subclass_defined_in_app(widget_session) -> None:
    # as_widget() dispatches on the concrete class's package; a Plotter
    # subclass defined in an app has no AS_WIDGET_MAP entry, so dispatch
    # falls back to a pyvista class in the MRO
    class AppPlotter(pv.Plotter):  # type: ignore[misc]
        pass

    pl = AppPlotter(notebook=True, window_size=[400, 300])
    pl.add_mesh(pv.Sphere())
    with session_context(widget_session):
        w = as_widget(pl)
    assert isinstance(w, HTML)
    assert 'class="pyvista"' in w.value


def test_as_widget_pyvista_leaves_asyncio_unpatched(widget_session) -> None:
    # trame_pyvista's own launcher (elegantly_launch) patches asyncio
    # process-wide via nest_asyncio2 when it starts the shared trame server.
    # shinywidgets starts that server itself, so asyncio must stay untouched.
    import asyncio

    run_before = asyncio.run
    coerce_plotter(widget_session, make_plotter())
    assert asyncio.run is run_before


def test_as_widget_pyvista_reuses_trame_server(widget_session) -> None:
    # The shared trame server is started once (localhost-only, ephemeral port)
    # and reused across renders, not relaunched per render
    from trame_pyvista.widgets import get_server

    coerce_plotter(widget_session, make_plotter())
    server = get_server(pv.global_theme.trame.jupyter_server_name)
    assert server.running
    coerce_plotter(widget_session, make_plotter())
    assert get_server(pv.global_theme.trame.jupyter_server_name) is server
    assert server.port != 0


def test_as_widget_pyvista_closes_plotter_on_export_failure(
    widget_session, monkeypatch
) -> None:
    import trame_pyvista.jupyter

    def failing_show_trame(*args: object, **kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(trame_pyvista.jupyter, "show_trame", failing_show_trame)
    pl = make_plotter()
    with pytest.raises(RuntimeError, match="boom"):
        coerce_plotter(widget_session, pl)
    # The plotter is closed even though the export raised
    assert pl._closed


def test_as_widget_pyvista_closes_plotter_on_unexpected_widget(
    widget_session, monkeypatch
) -> None:
    import trame_pyvista.jupyter

    monkeypatch.setattr(
        trame_pyvista.jupyter, "show_trame", lambda *args, **kwargs: object()
    )
    pl = make_plotter()
    with pytest.raises(TypeError, match="html jupyter backend"):
        coerce_plotter(widget_session, pl)
    assert pl._closed


def test_as_widget_pyvista_closes_plotter_on_server_start_failure(
    widget_session, monkeypatch
) -> None:
    import shinywidgets._as_widget

    def failing_ensure_server() -> None:
        raise TimeoutError("trame server didn't start")

    monkeypatch.setattr(
        shinywidgets._as_widget, "ensure_pyvista_trame_server", failing_ensure_server
    )
    pl = make_plotter()
    with pytest.raises(TimeoutError, match="didn't start"):
        coerce_plotter(widget_session, pl)
    # The plotter is closed even though the server never started
    assert pl._closed


def test_as_widget_pyvista_passthrough_widget(widget_session) -> None:
    w = coerce_plotter(widget_session, make_plotter())
    assert as_widget(w) is w


def test_as_widget_pyvista_rejects_non_plotter() -> None:
    with pytest.raises(TypeError, match="Plotter"):
        as_widget_pyvista(object())


def test_as_widget_pyvista_error_names_type_not_repr() -> None:
    # A pyvista mesh repr is a multi-line stats dump; the error should name
    # the type instead of flooding the Shiny error box with mesh stats
    with pytest.raises(TypeError) as excinfo:
        as_widget_pyvista(pv.Sphere())
    msg = str(excinfo.value)
    assert "PolyData" in msg
    assert "an ipywidget" in msg
    assert "\n" not in msg


def test_as_widget_pyvista_rejects_closed_plotter(widget_session) -> None:
    pl = make_plotter()
    coerce_plotter(widget_session, pl)
    # Coercion closed the plotter; reusing it should fail with a helpful
    # message, not trame_pyvista's "Do not call 'show()' ..." RuntimeError
    assert pl._closed
    with pytest.raises(ValueError, match="fresh Plotter"):
        as_widget_pyvista(pl)


def test_pyvista_layout_defaults_fill(widget_session) -> None:
    w = coerce_plotter(widget_session, make_plotter())
    _, fill = set_layout_defaults(w)
    assert fill is True


def test_pyvista_layout_defaults_ignores_other_widgets(widget_session) -> None:
    # The handler is keyed on the widget's package; a foreign widget reaching
    # it must pass the fill decision through untouched
    with session_context(widget_session):
        w = HTML()
        w.layout.height = "50px"
        assert pyvista_layout_defaults(w, True) is True


def test_pyvista_layout_defaults_respects_user_height(widget_session) -> None:
    w = coerce_plotter(widget_session, make_plotter())
    assert isinstance(w, Widget)
    w.layout.height = "300px"
    _, fill = set_layout_defaults(w)
    assert fill is False


# trame-pyvista >= 0.3 renders through an anywidget EmbeddableWidget whose
# `_viewer_page` trait references a process-wide singleton
# (trame_pyvista.jupyter._get_viewer_page(), caching the vtk.js runtime so
# it isn't resent on every render). shinywidgets must treat that singleton as
# process-global, or a second session can never display it: see
# is_pyvista_viewer_page() and is_process_global_construction() in
# _shinywidgets.py.


def test_viewer_page_is_process_global(widget_session, fresh_viewer_page: None) -> None:
    w = coerce_plotter(widget_session, make_plotter())
    viewer_page = w._viewer_page
    assert viewer_page is not None
    assert sw.is_process_global(viewer_page)
    assert sw.SHARED_WIDGETS.get(viewer_page.model_id) is viewer_page


def test_viewer_page_reaches_second_concurrent_session(
    widget_session, other_session, fresh_viewer_page: None
) -> None:
    from tests.unit.test_shared_widgets import flush, render_in

    # Session A renders first, constructing (and caching) the viewer page
    render_in(widget_session, make_plotter)
    flush()

    # Before the fix: session B's render raises RuntimeError("_ViewerPage
    # belongs to another Shiny session, so it can't be displayed here.")
    # because the viewer page is still owned by session A.
    render_in(other_session, make_plotter)
    flush()


def test_viewer_page_survives_owning_sessions_close(
    widget_session, other_session, fresh_viewer_page: None
) -> None:
    from tests.unit.test_shared_widgets import flush, render_in

    render_in(widget_session, make_plotter)
    flush()
    run(widget_session.close())

    # Before the fix: the viewer page belonged to widget_session and was
    # closed along with it, so this raises RuntimeError("_ViewerPage was
    # closed (its render was invalidated, or it was closed explicitly), so
    # it can't be displayed again."). In production this breaks the app for
    # every visitor after the first one leaves, until the server restarts.
    render_in(other_session, make_plotter)
    flush()
