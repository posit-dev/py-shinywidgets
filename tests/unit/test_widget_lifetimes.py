"""
Widget lifetimes with a real Shiny session: render-constructed widgets (and the
Layout/Style models created lazily while serializing them) close when their
render is invalidated, while `session_lifetime()` widgets survive.
"""

from __future__ import annotations

import asyncio
import contextvars
from collections.abc import Coroutine
from typing import Any, TypeVar

import pytest
from ipywidgets import HTML, Button, VBox
from ipywidgets.widgets.widget import _instances
from shiny import App, Session, reactive, ui
from shiny._connection import MockConnection
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets import session_lifetime
from shinywidgets._comm import OrphanedShinyComm, ShinyComm
from shinywidgets._render_widget_base import (
    WidgetRenderContext,
    is_closed_widget,
    render_widget_base,
)
from shinywidgets._shinywidgets import COMM_MANAGERS, KEPT_WIDGETS

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
    from ipywidgets.widgets.widget import widget_serialization
    from shinywidgets._shinywidgets import referenced_widgets
    from traitlets import Dict

    class Holder(HTML):
        # Tagged with the widget (de)serializer, like `children`/`layout`/`style`
        # traits are, so this trait can legitimately carry widget references
        # (see test_referenced_widgets_ignores_traits_without_to_json below for
        # a trait that can't).
        data = Dict().tag(sync=True, **widget_serialization)

    with session_context(widget_session):
        inner = HTML(value="inner")
        cyclic: dict[str, object] = {"inner": inner}
        cyclic["self"] = cyclic
        holder = Holder(data=cyclic)
    assert referenced_widgets([holder]) == {id(holder), id(inner)}


def test_referenced_widgets_ignores_traits_without_to_json(
    widget_session: Session,
) -> None:
    """
    Only walk traits with a `to_json` serializer. A widget placed in a
    plain (untagged) Dict/List trait can't actually reach the browser -- it fails
    `json_packer` -- so such a trait can't hold a live widget reference and isn't
    worth walking (this also skips expensive opaque payloads like GeoJSON `data`
    or Altair specs).
    """
    from shinywidgets._shinywidgets import referenced_widgets
    from traitlets import Dict

    class Holder(HTML):
        data = Dict().tag(sync=True)

    with session_context(widget_session):
        child = HTML(value="child")
        holder = Holder(data={"child": child})
    assert referenced_widgets([holder]) == {id(holder)}


def test_kept_borrowed_widget_is_rechecked_and_closed_once_dropped(
    widget_session: Session,
) -> None:
    """
    A session-owned container rebuilds its one child on every
    render. When a render is invalidated, its old child is still referenced by
    the live container, so it's kept rather than closed -- but nothing used to
    re-examine it once the container moved on to a new child, leaking one widget
    per render forever.
    """
    with session_context(widget_session):
        with session_lifetime():
            container = VBox()

        first_ctx = Context()
        with first_ctx(), WidgetRenderContext():
            button1 = Button(description="child 0")
            container.children = (button1,)
        flush()
        assert is_open(button1)

        # Invalidating the first render's context (as happens when the next
        # render is about to replace button1) keeps button1: the container
        # still references it at this point -- the next render hasn't rebuilt
        # `children` yet.
        first_ctx.invalidate()
        flush()
        assert is_open(button1)
        assert widget_session.id in KEPT_WIDGETS

        second_ctx = Context()
        with second_ctx(), WidgetRenderContext():
            button2 = Button(description="child 1")
            container.children = (button2,)  # drops button1's reference
        flush()
        assert is_open(button1)  # not yet rechecked

        # Invalidating the *next* render (as happens when a third render is
        # about to replace button2) re-checks the kept list: button1 is
        # no longer referenced by anything, so it closes as part of this sweep.
        # button2 is still referenced by container, so it's the new kept widget
        # -- there's always one render's lag between a child being dropped and
        # its sweep.
        second_ctx.invalidate()
        flush()
    assert not is_open(button1)
    assert is_open(button2)
    assert button1 not in KEPT_WIDGETS[widget_session.id]
    assert button2 in KEPT_WIDGETS[widget_session.id]


def test_sweep_only_walks_this_sessions_widgets(widget_session: Session) -> None:
    """
    The sweep's root set is this session's own live widgets, not every
    widget in the process. A widget from another session that happens to
    reference a to-be-closed widget must not keep it alive.
    """
    other = App(ui.page_fluid(), widget_test_server)._create_session(MockConnection())
    try:
        with session_context(widget_session):
            context = Context()
            with context(), WidgetRenderContext():
                button = Button(description="mine")
            flush()

        with session_context(other):
            # A widget in another session referencing `button` (e.g. by a mistake
            # like a module-level cache shared across sessions).
            VBox(children=(button,))
            flush()

        with session_context(widget_session):
            context.invalidate()
            flush()
        assert not is_open(button)
    finally:
        run(other.close())


def test_widget_built_in_already_invalidated_render_closes_immediately(
    widget_session: Session,
) -> None:
    """
    `Context.on_invalidate()` runs its callback immediately if
    the context is already invalidated. The render-owned-widgets list must
    already contain the widget being constructed by the time that callback can
    fire, or the widget is appended to an orphaned list and never closed.
    """
    with session_context(widget_session):
        context = Context()
        context.invalidate()
        with context(), WidgetRenderContext():
            widget = HTML(value="late")
        flush()
    assert not is_open(widget)
    assert widget.model_id not in _instances


def test_task_widget_shares_its_renders_cleanup(widget_session: Session) -> None:
    """
    A background task started during a render (e.g. streaming
    markers into a map) keeps a copy of the render's context (asyncio.create_task
    copies the current contextvars). A widget it builds after the render body
    returns must still share that render's cleanup, or it leaks until the
    session ends.
    """
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            first = Button(description="first")
            # Stand-in for asyncio.create_task(), which copies the current
            # contextvars snapshot at creation time.
            captured = contextvars.copy_context()
        flush()
        second = captured.run(lambda: Button(description="from a later task"))
        flush()
        assert is_open(first) and is_open(second)

        context.invalidate()
        flush()
    assert not is_open(first)
    assert not is_open(second)


def test_session_end_leaves_an_orphaned_comm(widget_session: Session) -> None:
    """
    Session-end cleanup uses the same close_widget() helper as
    render cleanup, leaving an OrphanedShinyComm behind instead of None, so
    `widget.model_id` (which packages like ipyleaflet read after closing) keeps
    working instead of raising AttributeError on a later session's deferred open.
    """
    with session_context(widget_session):
        widget = HTML(value="x")
        flush()

    run(widget_session.close())

    assert isinstance(widget.comm, OrphanedShinyComm)
    assert widget.model_id  # does not raise
    assert is_closed_widget(widget)
    assert widget_session.id not in KEPT_WIDGETS


def test_session_end_then_late_render_invalidation_does_not_reclose(
    widget_session: Session,
) -> None:
    """
    Shiny invalidates a session's output Contexts *after* on_ended cleanup runs.
    A render-owned widget is therefore closed once by session-end cleanup, and
    its render Context can still invalidate afterwards -- that must not call
    the widget's close() a second time (the OrphanedShinyComm session-end cleanup leaves looks "open"
    to a naive `comm is None` check, so close_render_widgets must use
    is_closed_widget() instead).
    """
    close_calls = 0

    class CleanupWidget(HTML):
        def close(self) -> None:
            nonlocal close_calls
            super().close()
            close_calls += 1

    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            CleanupWidget(value="resource")
        flush()
        assert close_calls == 0

        run(widget_session.close())
        assert close_calls == 1

        # Simulate Shiny invalidating the output's Context after on_ended.
        context.invalidate()
        flush()

    assert close_calls == 1
