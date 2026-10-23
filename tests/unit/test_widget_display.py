from __future__ import annotations

import asyncio
import json

import pytest
from ipywidgets import Widget
from plotly.graph_objects import FigureWidget, Scatter
from shiny import Session, reactive
from shiny.session import session_context
from shiny.session._session import AppSession
from shinywidgets._comm import ShinyComm
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
