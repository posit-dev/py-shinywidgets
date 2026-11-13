from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

import pytest
from ipywidgets import IntSlider, Widget
from plotly.graph_objects import FigureWidget, Scatter
from shiny import Session, reactive
from shiny.session import session_context
from shiny.session._session import AppSession
from shinywidgets._comm import OrphanedShinyComm, ShinyComm
from shinywidgets._shinywidgets import SESSION_WIDGET_ID_MAP


def test_open_does_not_create_display_previews(widget_session: Session) -> None:
    with session_context(widget_session):
        widget = PreviewWidget()
        asyncio.get_event_loop().run_until_complete(reactive.flush())

    assert isinstance(widget.comm, ShinyComm)
    assert SESSION_WIDGET_ID_MAP[widget_session.id] == [widget.model_id]


@pytest.mark.parametrize("use_subclass", [False, True], ids=["plotly", "subclass"])
def test_plotly_open_sends_changes_made_before_flush(
    widget_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    use_subclass: bool,
) -> None:
    messages: list[str] = []

    async def send_custom_message(type: str, message: object) -> None:
        if type == "shinywidgets_comm_open":
            assert isinstance(message, str)
            messages.append(message)

    monkeypatch.setattr(widget_session, "send_custom_message", send_custom_message)
    assert isinstance(widget_session, AppSession)
    with session_context(widget_session):
        widget_class = CustomFigureWidget if use_subclass else FigureWidget
        widget = widget_class([Scatter(y=[1, 2])], layout={"title": "Before"})
        widget.data[0].y = [3, 4]
        widget.add_scatter(y=[5, 6])
        widget.layout.title.text = "After"
        asyncio.get_event_loop().run_until_complete(reactive.flush())
        asyncio.get_event_loop().run_until_complete(
            widget_session._flush_callbacks.invoke()
        )

    state = next(
        msg["content"]["data"]["state"]
        for msg in map(json.loads, messages)
        if msg["content"]["comm_id"] == widget.model_id
    )
    assert [trace["y"] for trace in state["_widget_data"]] == [[3, 4], [5, 6]]
    assert state["_widget_layout"]["title"]["text"] == "After"


class PreviewWidget(Widget):
    def _repr_mimebundle_(self, **kwargs: object) -> dict[str, object]:
        preview = Widget()
        return {
            "application/vnd.jupyter.widget-view+json": {
                "version_major": 2,
                "version_minor": 0,
                "model_id": preview.model_id,
            }
        }


class CustomFigureWidget(FigureWidget):
    pass


SANITIZED_MSG = "An error has occurred. Check your logs or contact the app author for clarification."


class BrokenStateSlider(IntSlider):
    def get_state(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("boom during get_state")


def test_comm_open_failure_notifies_user(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: List[Dict[str, Any]] = []
    monkeypatch.setattr(widget_session, "_send_message_sync", sent.append)

    async def unhandled(e: Exception) -> None:
        raise AssertionError(f"session must survive a comm-open failure: {e}")

    monkeypatch.setattr(widget_session, "_unhandled_error", unhandled)

    with session_context(widget_session):
        _ = BrokenStateSlider()
        asyncio.get_event_loop().run_until_complete(reactive.flush())

    [note] = [m for m in sent if "notification" in m]
    payload = note["notification"]["message"]
    assert payload["type"] == "error"
    assert payload["duration"] is None
    assert "boom during get_state" in payload["html"]


def test_comm_open_failure_stops_queuing_sends(widget_session: Session) -> None:
    with session_context(widget_session):
        w = BrokenStateSlider()
        asyncio.get_event_loop().run_until_complete(reactive.flush())
        w.send({"x": 1})

    assert isinstance(w.comm, OrphanedShinyComm)
    assert w.comm.take_queued_sends() == []


def test_comm_open_failure_notification_is_sanitized_with_app_flag(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    widget_session.app.sanitize_errors = True
    sent: List[Dict[str, Any]] = []
    monkeypatch.setattr(widget_session, "_send_message_sync", sent.append)

    with session_context(widget_session):
        _ = BrokenStateSlider()
        asyncio.get_event_loop().run_until_complete(reactive.flush())

    [note] = [m for m in sent if "notification" in m]
    assert note["notification"]["message"]["html"] == SANITIZED_MSG
