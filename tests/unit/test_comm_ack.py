from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterator, Optional, cast

import pytest
import shinywidgets._shinywidgets as sw
from shiny import Session
from shinywidgets._comm import ShinyComm, ShinyCommManager

from ._fakes import FakeSession


def run_flushed(session: FakeSession) -> None:
    for fn in list(session._flushed_handlers):
        result = fn()
        if asyncio.iscoroutine(result):
            asyncio.run(result)


def client_msg(
    comm_id: str, msg_id: Optional[str] = "c1-7", msg_type: str = "comm_msg"
) -> Dict[str, Any]:
    header: Dict[str, str] = {"msg_type": msg_type}
    if msg_id is not None:
        header["msg_id"] = msg_id
    return {
        "header": header,
        "content": {"comm_id": comm_id, "data": {}},
        "buffers": [],
    }


def handle(session: FakeSession, msg: Dict[str, Any]) -> None:
    sw.handle_client_comm_msg(cast(Session, session), msg)


@pytest.fixture
def session() -> Iterator[FakeSession]:
    s = FakeSession()
    sw.COMM_MANAGERS[s.id] = ShinyCommManager()
    yield s
    sw.COMM_MANAGERS.pop(s.id)


def test_ack_sent_after_flush_for_unknown_comm(session: FakeSession) -> None:
    handle(session, client_msg("nope"))
    assert session.custom_messages == []
    run_flushed(session)
    assert session.custom_messages == [
        ("shinywidgets_comm_ack", {"comm_id": "nope", "msg_id": "c1-7"})
    ]


def test_no_ack_without_msg_id(session: FakeSession) -> None:
    handle(session, client_msg("nope", msg_id=None))
    run_flushed(session)
    assert session.custom_messages == []


def test_ack_sent_even_when_handler_raises(session: FakeSession) -> None:
    class Boom:
        def handle_msg(self, msg: object) -> None:
            raise RuntimeError("handler failed")

    sw.COMM_MANAGERS[session.id].comms["c1"] = cast(ShinyComm, Boom())
    with pytest.raises(RuntimeError, match="handler failed"):
        handle(session, client_msg("c1"))
    run_flushed(session)
    assert [t for t, _ in session.custom_messages] == ["shinywidgets_comm_ack"]


def test_ack_registered_after_handler_scheduled_sends(session: FakeSession) -> None:
    class Echoing:
        def handle_msg(self, msg: object) -> None:
            session.on_flushed(lambda: session.custom_messages.append(("echo", "")))

    sw.COMM_MANAGERS[session.id].comms["c1"] = cast(ShinyComm, Echoing())
    handle(session, client_msg("c1"))
    run_flushed(session)
    assert [t for t, _ in session.custom_messages] == [
        "echo",
        "shinywidgets_comm_ack",
    ]
