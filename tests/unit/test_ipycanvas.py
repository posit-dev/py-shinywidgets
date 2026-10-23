from __future__ import annotations

import asyncio
import subprocess
import sys

import pytest
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny.session import session_context

pytest.importorskip("ipycanvas")


def test_import_ipycanvas_after_shinywidgets() -> None:
    # Importing ipycanvas constructs a module-level _CanvasManager widget,
    # which must be tolerated outside a Shiny session
    script = "import shinywidgets\nimport ipycanvas\n"
    subprocess.run([sys.executable, "-c", script], check=True)


def render_one(renderer: rwb.render_widget_base, value: object) -> dict[str, object]:
    @renderer
    def _():  # noqa: ANN202
        return value

    return asyncio.run(renderer._render())  # type: ignore


def test_render_ipycanvas_is_render_widget_base() -> None:
    renderer = rw.render_ipycanvas()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipycanvas_passes_canvas_through(widget_session) -> None:
    from ipycanvas import Canvas

    r = rw.render_ipycanvas()
    with session_context(widget_session):
        canvas = Canvas(width=320, height=240)
        res = render_one(r, canvas)

    assert res is not None
    assert r.widget is canvas
    assert res["widget_pkg"] == "ipycanvas"
    # The output fills its container (the canvas itself is centered inside it,
    # at its natural pixel size)
    assert res["fill"] is True


def test_render_ipycanvas_accepts_all_canvas_classes(widget_session) -> None:
    from ipycanvas import Canvas, MultiCanvas, MultiRoughCanvas, RoughCanvas

    for cls in (Canvas, MultiCanvas, RoughCanvas, MultiRoughCanvas):
        r = rw.render_ipycanvas()
        with session_context(widget_session):
            res = render_one(r, cls())
        assert res is not None
        assert isinstance(r.widget, cls)


def test_ipycanvas_layout_defaults_add_centering_class(widget_session) -> None:
    from ipycanvas import Canvas

    with session_context(widget_session):
        canvas = Canvas()
        widget, fill = rwb.set_layout_defaults(canvas)

    assert fill is True
    assert "shinywidgets-ipycanvas" in widget._dom_classes


def test_canvas_gets_own_draw_command_manager(widget_session) -> None:
    import ipycanvas.canvas
    import shinywidgets._shinywidgets as sw
    from ipycanvas import Canvas

    with session_context(widget_session):
        canvas = Canvas()
        other = Canvas()

    # Each canvas gets its own manager, not the module-level one ipycanvas
    # shares across canvases (which has no comm and would leak draw commands
    # across sessions)
    manager = canvas._canvas_manager
    assert manager is not ipycanvas.canvas._CANVAS_MANAGER
    assert manager is not other._canvas_manager
    # ... and it belongs to this session, so the canvas passes the
    # foreign/closed-widget check and the manager's comm opens on flush
    assert manager._model_id in sw.SESSION_WIDGET_ID_MAP[widget_session.id]
    assert sw.foreign_or_closed_widget(canvas, widget_session) is None


def test_ipycanvas_explicit_layout_height_opts_out_of_fill(widget_session) -> None:
    from ipycanvas import Canvas

    with session_context(widget_session):
        canvas = Canvas()
        canvas.layout.height = "200px"
        _, fill = rwb.set_layout_defaults(canvas)

    assert fill is False
