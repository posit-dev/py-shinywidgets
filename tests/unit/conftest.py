# Shared, generic fixtures/helpers for unit tests should live here.

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from typing import Any, Callable

import pytest
import shinywidgets._shinywidgets as sw
from shiny import App, Inputs, Outputs, Session, reactive, ui
from shiny._connection import MockConnection
from shiny.session import session_context


def widget_test_server(input: Inputs, output: Outputs, session: Session) -> None:
    pass


@pytest.fixture
def widget_session(monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    """
    A real (non-stub) Shiny session backed by a MockConnection, so tests can
    construct real ipywidgets and drive reactive flushes/invalidation.
    """
    app = App(ui.page_fluid(), widget_test_server)
    session = app._create_session(MockConnection())
    monkeypatch.setattr(sw, "SHINYWIDGETS_CDN_ONLY", True)
    # Session effects send busy-count messages when scheduled, which needs a
    # current event loop (a real Shiny app always runs with one).
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield session
    finally:
        asyncio.run(session.close())
        asyncio.set_event_loop(loop)
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture
def flush_to_browser(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> Callable[[], list[dict[str, Any]]]:
    """
    Run a reactive flush cycle, returning every comm message `widget_session`
    has sent its browser so far (each with its custom message `type`), in the
    order sent.
    """
    sent: list[dict[str, Any]] = []

    async def record(msg_type: str, msg_txt: str) -> None:
        sent.append({"type": msg_type, **json.loads(msg_txt)})

    monkeypatch.setattr(widget_session, "send_custom_message", record)

    def flush() -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()
        with session_context(widget_session):
            loop.run_until_complete(reactive.flush())
            loop.run_until_complete(widget_session._flush_callbacks.invoke())
            loop.run_until_complete(widget_session._flushed_callbacks.invoke())
        return sent

    return flush


@pytest.fixture
def shared_state() -> Iterator[None]:
    """Close and forget the process-global widgets a test creates."""
    before = dict(sw.SHARED_WIDGETS)
    try:
        yield
    finally:
        for model_id, w in list(sw.SHARED_WIDGETS.items()):
            if before.get(model_id) is not w:
                w.close()
        sw.SHARED_WIDGETS.clear()
        sw.SHARED_WIDGETS.update(before)


def reads_across_rerender(
    r: Any, first: object, second: object, read: Callable[[], Any]
) -> list[Any]:
    """
    What a reactive reader of `read()` sees on each of its runs when the output
    `r` renders `first` and then re-renders with `second`.
    """
    seen: list[Any] = []

    def render(widget: object) -> None:  # stands in for _render()
        r._widget = widget
        r._invalidate_contexts()
        r._accessors.on_render(widget)

    render(first)

    @reactive.effect(session=None)
    def reader() -> None:
        seen.append(read())

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(reactive.flush())
        render(second)
        loop.run_until_complete(reactive.flush())
    finally:
        reader.destroy()
    return seen
