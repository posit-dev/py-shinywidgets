# Shared, generic fixtures/helpers for unit tests should live here.

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
import shinywidgets._shinywidgets as sw
from shiny import App, Inputs, Outputs, Session, ui
from shiny._connection import MockConnection


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
