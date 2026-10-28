from __future__ import annotations

import pytest
from shiny import Session
from shiny.session import session_context
from shinywidgets import render_pythreejs


def make_renderer():
    p3 = pytest.importorskip("pythreejs")
    return p3.Renderer(
        scene=p3.Scene(),
        camera=p3.PerspectiveCamera(position=[3, 3, 3]),
    )


def test_render_pythreejs_passes_a_renderer_through(widget_session: Session) -> None:
    # A pythreejs Renderer is already a widget, so there's no coercion
    p3 = pytest.importorskip("pythreejs")

    with session_context(widget_session):
        renderer = make_renderer()
        assert render_pythreejs()._as_widget(renderer) is renderer

        # ... and .widget is typed as (and actually is) the Renderer
        r = render_pythreejs()

        @r
        def _():  # noqa: ANN202
            return make_renderer()

        import asyncio

        assert asyncio.run(r._render()) is not None
        assert isinstance(r.widget, p3.Renderer)
