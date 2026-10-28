from __future__ import annotations

import base64
import json
from typing import Any, Dict, List

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


def test_update_messages_are_coalesced(monkeypatch):
    """Multiple method='update' sends for the same comm_id produce one flushed callback."""
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    c.send(data={"method": "update", "state": {"a": 1}, "buffer_paths": []})
    c.send(data={"method": "update", "state": {"a": 2, "b": 3}, "buffer_paths": []})

    # Only one flushed callback despite two sends
    assert len(session._flushed_handlers) == 1

    # The pending entry should have the merged state
    pending = comm._get_pending_updates(session)
    assert "c1" in pending
    assert pending["c1"]["data"]["state"] == {"a": 2, "b": 3}


def test_coalesced_state_merges_across_traits(monkeypatch):
    """Updates to different traits are merged, not replaced."""
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    c.send(data={"method": "update", "state": {"x": 10}, "buffer_paths": []})
    c.send(data={"method": "update", "state": {"y": 20}, "buffer_paths": []})

    pending = comm._get_pending_updates(session)
    assert pending["c1"]["data"]["state"] == {"x": 10, "y": 20}


def test_coalescing_handles_buffers(monkeypatch):
    """Buffer paths for overridden keys are replaced; others are preserved."""
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    c.send(
        data={
            "method": "update",
            "state": {"img": None, "label": "old"},
            "buffer_paths": [["img"]],
        },
        buffers=[b"\x00\x01"],
    )
    # Override "img" with new buffer; "label" stays from first message
    c.send(
        data={
            "method": "update",
            "state": {"img": None},
            "buffer_paths": [["img"]],
        },
        buffers=[b"\x02\x03"],
    )

    pending = comm._get_pending_updates(session)
    entry = pending["c1"]
    assert entry["data"]["state"] == {"img": None, "label": "old"}
    assert entry["data"]["buffer_paths"] == [["img"]]
    assert entry["buffers"] == [b"\x02\x03"]


def test_non_update_messages_are_not_coalesced(monkeypatch):
    """Custom-method messages bypass coalescing and get their own callbacks."""
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    c.send(data={"method": "custom", "content": {"event": "click"}})
    c.send(data={"method": "custom", "content": {"event": "hover"}})

    # Each non-update message gets its own flushed callback
    assert len(session._flushed_handlers) == 2


def test_different_comm_ids_coalesce_independently(monkeypatch):
    """Updates for different models each get their own coalesced entry."""
    import shinywidgets._comm as comm

    session = FakeSession()

    mgr = comm.ShinyCommManager()
    c1 = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    c2 = comm.ShinyComm(
        comm_id="c2", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    c1.send(data={"method": "update", "state": {"a": 1}, "buffer_paths": []})
    c2.send(data={"method": "update", "state": {"a": 2}, "buffer_paths": []})
    c1.send(data={"method": "update", "state": {"a": 3}, "buffer_paths": []})

    # Two flushed callbacks (one per comm_id)
    assert len(session._flushed_handlers) == 2

    pending = comm._get_pending_updates(session)
    assert pending["c1"]["data"]["state"] == {"a": 3}
    assert pending["c2"]["data"]["state"] == {"a": 2}


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
    import asyncio

    import shinywidgets._comm as comm

    session = FakeSession()
    sent: List[tuple[str, str]] = []

    async def record(msg_type: str, msg_txt: str) -> None:
        sent.append((msg_type, msg_txt))

    session.send_custom_message = record  # type: ignore[method-assign]
    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    c.on_msg(lambda msg: c.send(data={"method": "echo_update"}))
    session._flush_handlers.clear()

    header = {"msg_id": "c1:7"}
    c.handle_msg({"header": header, "content": {"comm_id": "c1", "data": {}}})
    # a state update, which is coalesced and so only built when the flush ends
    c.send(data={"method": "update", "state": {"x": 1}, "buffer_paths": []})

    echo_handler, update_handler = session._flushed_handlers
    echo = json.loads(closure_map(echo_handler)["msg_txt"])
    assert echo["parent_header"] == header

    asyncio.run(update_handler())
    ((msg_type, msg_txt),) = sent
    assert msg_type == "shinywidgets_comm_msg"
    assert "parent_header" not in json.loads(msg_txt)


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
