from __future__ import annotations

import asyncio
from typing import Literal

import pytest
from ipywidgets import HTML
from shiny import Session, reactive
from shiny.session import session_context
from shinywidgets._lifecycle import get_lifecycle


@pytest.mark.parametrize("trigger", ["widget", "comm", "session"])
def test_close_runs_override_cleanup_once(
    widget_session: Session, trigger: Literal["widget", "comm", "session"]
) -> None:
    with session_context(widget_session):
        widget = CleanupWidget(value="resource")
        model_id = widget.model_id
        asyncio.run(reactive.flush())
        lifecycle = get_lifecycle(widget_session)
        if trigger == "widget":
            widget.close()
        elif trigger == "comm":
            assert widget.comm is not None
            widget.comm.close()
        else:
            lifecycle.close_session()
        widget.close()
        widget.close()

    assert widget.cleanup_calls == 1
    assert model_id not in lifecycle.records
    assert model_id not in lifecycle.comm_manager.comms


class CleanupWidget(HTML):
    cleanup_calls: int = 0

    def close(self) -> None:
        super().close()
        self.cleanup_calls += 1
