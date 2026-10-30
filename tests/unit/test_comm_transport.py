from __future__ import annotations

import base64
import json
from typing import Any, Dict

import pytest

from tests.unit._fakes import FakeSession


def closure_map(fn: Any) -> Dict[str, Any]:
    freevars = getattr(fn.__code__, "co_freevars", ())
    closure = fn.__closure__ or ()
    return {name: cell.cell_contents for name, cell in zip(freevars, closure)}


def _scheduled_payloads(session: FakeSession):
    return {
        "flush": list(session._flush_handlers),
        "flushed": list(session._flushed_handlers),
    }


def test_open_registers_and_schedules_on_flush(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    _ = comm.ShinyComm(
        comm_id="c1",
        comm_manager=mgr,
        target_name="jupyter.widget",
        session=session,
        data={"a": 1},
    )

    assert "c1" in mgr.comms
    payloads = _scheduled_payloads(session)
    assert len(payloads["flush"]) == 1
    assert len(payloads["flushed"]) == 0

    cells = closure_map(payloads["flush"][0])
    assert cells["msg_type"] == "shinywidgets_comm_open"
    msg = json.loads(cells["msg_txt"])
    assert msg["content"]["comm_id"] == "c1"
    assert msg["content"]["data"] == {"a": 1}
    assert msg["content"]["target_name"] == "jupyter.widget"
    assert msg["content"]["target_module"] is None
    assert msg["buffers"] == []
    assert msg["ident"] == "comm-c1"


def test_send_schedules_on_flushed(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()

    c.send(data={"k": "v"})
    payloads = _scheduled_payloads(session)
    assert len(payloads["flushed"]) == 1
    cells = closure_map(payloads["flushed"][0])
    assert cells["msg_type"] == "shinywidgets_comm_msg"
    msg = json.loads(cells["msg_txt"])
    assert msg["content"]["comm_id"] == "c1"
    assert msg["content"]["data"] == {"k": "v"}


def test_close_is_idempotent_and_unregisters(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    c.close()
    assert "c1" not in mgr.comms

    # Second close is a no-op (does not schedule a second message).
    n = len(session._flushed_handlers)
    c.close()
    assert len(session._flushed_handlers) == n


def test_close_is_suppressed_when_id_reregistered(monkeypatch):
    import asyncio

    import shinywidgets._comm as comm

    session = FakeSession()

    sent: list[str] = []

    async def _spy(msg_type: str, msg_txt: str) -> None:
        sent.append(msg_type)

    monkeypatch.setattr(session, "send_custom_message", _spy)

    mgr = comm.ShinyCommManager()
    old = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    # A replacement widget re-created with the same (explicit) id registers a
    # new comm for it.
    new = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    # Closing the old comm still schedules a close, but at send time the id
    # belongs to the new comm, so nothing is sent and the new comm stays
    # registered.
    old.close()
    assert len(session._flushed_handlers) == 1
    asyncio.run(session._flushed_handlers[0]())
    assert sent == []
    assert mgr.comms.get("c1") is new

    # Closing the current owner of the id sends the close.
    new.close()
    assert len(session._flushed_handlers) == 2
    asyncio.run(session._flushed_handlers[1]())
    assert sent == ["shinywidgets_comm_close"]
    assert "c1" not in mgr.comms


def test_close_does_not_publish_after_session_ended():
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flushed_handlers.clear()

    mgr.active = False
    c.close()
    assert len(session._flushed_handlers) == 0
    assert "c1" not in mgr.comms


def test_open_unregisters_if_publish_fails():
    import shinywidgets._comm as comm

    class BrokenSession(FakeSession):
        def on_flush(self, fn):  # type: ignore[override]
            raise RuntimeError("connection gone")

    mgr = comm.ShinyCommManager()
    with pytest.raises(RuntimeError, match="connection gone"):
        comm.ShinyComm(
            comm_id="c1",
            comm_manager=mgr,
            target_name="jupyter.widget",
            session=BrokenSession(),
        )
    assert "c1" not in mgr.comms


def test_buffers_are_base64_encoded_and_validated(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    c.send(data={"buffer_paths": [["x"]]}, buffers=[b"\x00\x01"])
    cells = closure_map(session._flushed_handlers[0])
    msg = json.loads(cells["msg_txt"])
    assert msg["buffers"] == [base64.b64encode(b"\x00\x01").decode("ascii")]

    # Non-contiguous buffers must raise.
    # `_comm.py` checks `isinstance(buf, memoryview)` and then calls `memoryview(buf)`,
    # so patch the module-global name to a type that returns a non-contiguous "view".
    class _NonContiguousView:
        contiguous = False

        def __new__(cls, obj):  # noqa: D401
            return super().__new__(cls)

    monkeypatch.setattr(comm, "memoryview", _NonContiguousView, raising=False)
    with pytest.raises(ValueError):
        c.send(buffers=[bytearray(b"abcd")])

    # Non-buffer-protocol object must raise.
    monkeypatch.delattr(comm, "memoryview", raising=False)
    with pytest.raises(TypeError):
        c.send(buffers=[object()])  # type: ignore[list-item]


def test_msg_and_close_callbacks(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )

    seen: Dict[str, Any] = {"msg": None, "close": None}
    c.on_msg(lambda m: seen.__setitem__("msg", m))
    c.on_close(lambda m: seen.__setitem__("close", m))

    c.handle_msg({"hello": "world"})
    c.handle_close({"bye": "world"})
    assert seen["msg"] == {"hello": "world"}
    assert seen["close"] == {"bye": "world"}


def test_orphaned_shiny_comm_methods_are_noops() -> None:
    import shinywidgets._comm as comm

    orphan = comm.OrphanedShinyComm("c1")

    assert orphan.send() is None
    assert orphan.close() is None
    assert orphan.on_msg(lambda msg: msg) is None


def test_messages_go_to_the_session_that_opened_the_comm():
    import shinywidgets._comm as comm

    owner = FakeSession(session_id="owner")
    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=owner
    )
    owner._flush_handlers.clear()

    c.send(data={"x": 1})

    assert len(owner._flushed_handlers) == 1
    assert owner._flush_handlers == []


def test_messages_sent_while_handling_a_client_msg_carry_its_header():
    """
    The browser drops stale `echo_update`s by matching `parent_header.msg_id`
    against the id of its latest send; without a parent_header every echo is
    applied, so an older value can overwrite a newer one.
    """
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    c.on_msg(lambda msg: c.send(data={"method": "echo_update"}))
    session._flush_handlers.clear()

    header = {"msg_id": "c1:7"}
    c.handle_msg({"header": header, "content": {"comm_id": "c1", "data": {}}})
    c.send(data={"method": "update"})

    echo, later = (
        json.loads(closure_map(fn)["msg_txt"]) for fn in session._flushed_handlers
    )
    assert echo["parent_header"] == header
    assert "parent_header" not in later


def test_widget_echo_update_carries_the_client_msg_id(
    widget_session, monkeypatch: pytest.MonkeyPatch
):
    import asyncio

    from ipywidgets import IntSlider
    from shiny import reactive
    from shiny.session import session_context
    from shinywidgets._comm import ShinyComm

    sent: list[Dict[str, Any]] = []

    async def record(msg_type: str, msg_txt: str) -> None:
        sent.append({"type": msg_type, **json.loads(msg_txt)})

    monkeypatch.setattr(widget_session, "send_custom_message", record)
    loop = asyncio.get_event_loop()

    with session_context(widget_session):
        slider = IntSlider(value=1)
        loop.run_until_complete(reactive.flush())
        assert isinstance(slider.comm, ShinyComm)
        slider.comm.handle_msg(
            {
                "header": {"msg_id": "browser-msg-1"},
                "content": {
                    "comm_id": slider.comm.comm_id,
                    "data": {
                        "method": "update",
                        "state": {"value": 5},
                        "buffer_paths": [],
                    },
                },
                "buffers": [],
            }
        )
        loop.run_until_complete(widget_session._flushed_callbacks.invoke())

    [echo] = [m for m in sent if m["content"]["data"].get("method") == "echo_update"]
    assert echo["content"]["data"]["state"] == {"value": 5}
    assert echo["parent_header"] == {"msg_id": "browser-msg-1"}


def build_shared_comms():
    import shinywidgets._comm as comm

    shared = comm.SharedShinyComm("shared1")
    sessions: Dict[str, FakeSession] = {}
    managers: Dict[str, comm.ShinyCommManager] = {}
    comms: Dict[str, comm.ShinyComm] = {}
    for sid in ("a", "b"):
        sessions[sid] = FakeSession(session_id=sid)
        managers[sid] = comm.ShinyCommManager()
        comms[sid] = comm.ShinyComm(
            comm_id="shared1",
            comm_manager=managers[sid],
            target_name="jupyter.widget",
            session=sessions[sid],
        )
    return shared, sessions, managers, comms


def test_shared_comm_sends_only_to_active_sessions():
    shared, sessions, managers, comms = build_shared_comms()
    shared.add(comms["a"])
    shared.add(comms["b"])
    managers["b"].active = False
    for s in sessions.values():
        s._flushed_handlers.clear()

    shared.send(data={"k": 1})

    assert len(sessions["a"]._flushed_handlers) == 1
    assert len(sessions["b"]._flushed_handlers) == 0


def test_shared_comm_applies_callbacks_to_later_comms():
    shared, _, _, comms = build_shared_comms()

    def cb(msg: Dict[str, object]) -> None: ...

    def cb2(msg: Dict[str, object]) -> None: ...

    shared.on_msg(cb)
    shared.on_close(cb2)
    shared.add(comms["a"])

    assert comms["a"]._msg_callback is cb
    assert comms["a"]._close_callback is cb2


def test_shared_comm_drop_session():
    shared, _, _, comms = build_shared_comms()
    shared.add(comms["a"])
    shared.add(comms["b"])

    shared.drop_session("b")

    assert shared.has_session("a")
    assert not shared.has_session("b")
    shared.drop_session("b")


def test_shared_comm_close_is_noop():
    shared, sessions, _, comms = build_shared_comms()
    shared.add(comms["a"])
    shared.add(comms["b"])
    for s in sessions.values():
        s._flushed_handlers.clear()
        s._flush_handlers.clear()

    shared.close()

    assert comms["a"]._closed is False
    assert comms["b"]._closed is False
    for s in sessions.values():
        assert s._flushed_handlers == []
        assert s._flush_handlers == []


def test_when_comm_open_waits_for_the_real_comm() -> None:
    from shinywidgets._comm import (
        OrphanedShinyComm,
        run_comm_open_callbacks,
        when_comm_open,
    )

    class W:
        comm: object = OrphanedShinyComm("m1")

    calls: list[int] = []
    when_comm_open(W(), lambda: calls.append(1))
    assert calls == []
    run_comm_open_callbacks("m1")
    assert calls == [1]
    run_comm_open_callbacks("m1")  # runs once
    assert calls == [1]

    class Open:
        comm: object = object()

    when_comm_open(Open(), lambda: calls.append(2))
    assert calls == [1, 2]
