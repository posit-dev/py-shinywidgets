"""
Widget lifetimes with a real Shiny session: render-constructed widgets (and the
Layout/Style models created lazily while serializing them) close when their
render is invalidated, while `session_lifetime()` widgets survive.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

import pytest
from ipywidgets import HTML, Button
from ipywidgets.widgets.widget import _instances
from shiny import App, Session, reactive, ui
from shiny._connection import MockConnection
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets import session_lifetime
from shinywidgets._comm import ShinyComm
from shinywidgets._render_widget_base import WidgetRenderContext, render_widget_base
from shinywidgets._shinywidgets import COMM_MANAGERS

from tests.unit.conftest import widget_test_server

T = TypeVar("T")


def run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.get_event_loop().run_until_complete(coro)


def flush() -> None:
    run(reactive.flush())


def is_open(widget: object) -> bool:
    return isinstance(getattr(widget, "comm", None), ShinyComm)


def test_explicit_close_before_open_stays_closed(widget_session: Session) -> None:
    with session_context(widget_session):
        widget = HTML(value="pending")
        model_id = widget.model_id
        widget.close()
        flush()
    assert not is_open(widget)
    assert model_id not in _instances


def test_render_invalidation_closes_late_defaults(widget_session: Session) -> None:
    baseline = len(_instances)
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            button = Button(description="temporary")
        flush()
        # Serializing the button materialized its Layout and ButtonStyle.
        assert is_open(button.layout) and is_open(button.style)
        assert len(_instances) == baseline + 3
        context.invalidate()
        flush()
    assert len(_instances) == baseline


def test_session_lifetime_widget_survives_render_invalidation(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            temporary = HTML(value="temporary")
            with session_lifetime():
                retained = HTML(value="retained")
        flush()
        context.invalidate()
        flush()
        assert not is_open(temporary)
        assert is_open(retained)
        assert is_open(retained.layout)


def test_session_lifetime_requires_active_session() -> None:
    with pytest.raises(RuntimeError, match="requires an active Shiny session"):
        with session_lifetime():
            pass


def test_rendering_a_closed_widget_raises(widget_session: Session) -> None:
    renderer = render_widget_base()
    cache: dict[str, HTML] = {}

    @renderer
    def _() -> HTML:
        return cache.setdefault("a", HTML(value="cached without session_lifetime"))

    with session_context(widget_session):
        first = Context()
        with first():
            run(renderer.render())
        flush()
        first.invalidate()
        flush()
        with Context()():
            with pytest.raises(RuntimeError, match="session_lifetime"):
                run(renderer.render())


def test_live_widget_keeps_a_default_created_during_a_render(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            with session_lifetime():
                cached = Button(description="cached")
            # Touching .style here materializes it under the render, but the
            # cached (session) widget still references it.
            cached.style.button_color = "red"
        flush()
        context.invalidate()
        flush()
        assert is_open(cached)
        assert is_open(cached.style)


def test_each_session_has_its_own_comm_registry(widget_session: Session) -> None:
    other = App(ui.page_fluid(), widget_test_server)._create_session(MockConnection())
    try:
        with session_context(widget_session):
            mine = HTML(value="mine")
            flush()
        with session_context(other):
            theirs = HTML(value="theirs")
            flush()
        assert mine.model_id in COMM_MANAGERS[widget_session.id].comms
        assert theirs.model_id not in COMM_MANAGERS[widget_session.id].comms
        assert theirs.model_id in COMM_MANAGERS[other.id].comms
    finally:
        run(other.close())


def test_render_retired_before_open_never_opens(widget_session: Session) -> None:
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            widget = HTML(value="never opened")
            model_id = widget.model_id
        context.invalidate()
        flush()
    assert not is_open(widget)
    assert model_id not in _instances
    assert model_id not in COMM_MANAGERS[widget_session.id].comms


def test_reference_walk_tolerates_container_cycles(widget_session: Session) -> None:
    from shinywidgets._shinywidgets import referenced_widgets
    from traitlets import Dict

    class Holder(HTML):
        data = Dict().tag(sync=True)

    with session_context(widget_session):
        inner = HTML(value="inner")
        cyclic: dict[str, object] = {"inner": inner}
        cyclic["self"] = cyclic
        holder = Holder(data=cyclic)
    assert referenced_widgets([holder]) == {id(holder), id(inner)}
