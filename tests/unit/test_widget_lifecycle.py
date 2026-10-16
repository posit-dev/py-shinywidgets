from __future__ import annotations

import asyncio

from ipywidgets import HTML
from shiny import Session, reactive
from shiny.session import session_context
from shinywidgets._lifecycle import get_lifecycle


def test_explicit_close_cancels_pending_open(widget_session: Session) -> None:
    with session_context(widget_session):
        widget = HTML(value="pending")
        model_id = widget.model_id
        widget.close()
        asyncio.run(reactive.flush())
        lifecycle = get_lifecycle(widget_session)
    assert model_id not in lifecycle.comm_manager.comms
    assert model_id not in lifecycle.records
    assert lifecycle.snapshot().pending_initializers == 0
