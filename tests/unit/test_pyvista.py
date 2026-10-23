import pytest
from ipywidgets import HTML, Widget

pv = pytest.importorskip("pyvista")
pytest.importorskip("trame_pyvista")

pv.OFF_SCREEN = True

from shiny.session import session_context  # noqa: E402
from shinywidgets._as_widget import as_widget, as_widget_pyvista  # noqa: E402
from shinywidgets._render_widget_base import (  # noqa: E402
    pyvista_layout_defaults,
    set_layout_defaults,
)


def coerce_plotter(widget_session, pl: "pv.Plotter") -> Widget:
    with session_context(widget_session):
        return as_widget_pyvista(pl)


def make_plotter() -> "pv.Plotter":
    pl = pv.Plotter(notebook=True, window_size=[400, 300])
    pl.add_mesh(pv.Sphere())
    return pl


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
