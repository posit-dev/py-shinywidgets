from __future__ import annotations

import base64
import json
from typing import Any, Dict

import pytest
from shinywidgets._lifecycle import EpochIdentity

from tests.unit._fakes import FakeSession

EPOCH = EpochIdentity(session_id="s1", model_namespace="ns", epoch_id="ep")


def closure_map(fn: Any) -> Dict[str, Any]:
    freevars = getattr(fn.__code__, "co_freevars", ())
    closure = fn.__closure__ or ()
    return {name: cell.cell_contents for name, cell in zip(freevars, closure)}


def _scheduled_payloads(session: FakeSession):
    return {
        "flush": list(session._flush_handlers),
        "flushed": list(session._flushed_handlers),
    }


def test_open_registers_and_schedules_on_flush():
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    comm.ShinyComm(
        comm_id="c1",
        comm_manager=mgr,
        target_name="jupyter.widget",
        session=session,  # type: ignore[arg-type]
        epoch=EPOCH,
        data={"a": 1},
    )

    assert "c1" in mgr.comms
    payloads = _scheduled_payloads(session)
    assert len(payloads["flush"]) == 1
    assert len(payloads["flushed"]) == 0

    cells = closure_map(payloads["flush"][0])
    assert cells["msg_type"] == "shinywidgets_comm_open"
    assert cells["session"] is session
    packet = json.loads(cells["msg_txt"])
    assert packet["sw"] == 1
    assert packet["session_id"] == "s1"
    assert packet["model_namespace"] == "ns"
    assert packet["epoch_id"] == "ep"
    msg = packet["msg"]
    assert msg["content"]["comm_id"] == "c1"
    assert msg["content"]["data"] == {"a": 1}
    assert msg["content"]["target_name"] == "jupyter.widget"
    assert msg["content"]["target_module"] is None
    assert msg["buffers"] == []
    assert msg["ident"] == "comm-c1"


def test_send_schedules_on_flushed():
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1",
        comm_manager=mgr,
        target_name="jupyter.widget",
        session=session,  # type: ignore[arg-type]
        epoch=EPOCH,
    )
    session._flush_handlers.clear()

    c.send(data={"k": "v"})
    payloads = _scheduled_payloads(session)
    assert len(payloads["flushed"]) == 1
    cells = closure_map(payloads["flushed"][0])
    assert cells["msg_type"] == "shinywidgets_comm_msg"
    msg = json.loads(cells["msg_txt"])["msg"]
    assert msg["content"]["comm_id"] == "c1"
    assert msg["content"]["data"] == {"k": "v"}


def test_close_is_idempotent_and_unregisters():
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1",
        comm_manager=mgr,
        target_name="jupyter.widget",
        session=session,  # type: ignore[arg-type]
        epoch=EPOCH,
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    c.close()
    assert "c1" not in mgr.comms

    # Second close is a no-op (does not schedule a second message).
    n = len(session._flushed_handlers)
    c.close()
    assert len(session._flushed_handlers) == n


def test_close_notifies_and_unregister_checks_identity():
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    notified: list[str] = []
    c = comm.ShinyComm(
        comm_id="c1",
        comm_manager=mgr,
        target_name="jupyter.widget",
        session=session,  # type: ignore[arg-type]
        epoch=EPOCH,
        on_closed=lambda: notified.append("c1"),
    )
    c.close()
    assert notified == ["c1"]
    # The notification fires exactly once.
    c.close()
    assert notified == ["c1"]

    # An old channel cannot remove a different live channel with the same ID.
    other = comm.ShinyComm(
        comm_id="c1",
        comm_manager=mgr,
        target_name="jupyter.widget",
        session=session,  # type: ignore[arg-type]
        epoch=EPOCH,
    )
    assert mgr.unregister_comm(c) is None
    assert mgr.comms["c1"] is other


def test_close_does_not_publish_when_session_ended():
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1",
        comm_manager=mgr,
        target_name="jupyter.widget",
        session=session,  # type: ignore[arg-type]
        epoch=EPOCH,
    )
    session._flushed_handlers.clear()

    # Session termination disables new sends before records are closed.
    mgr.active = False
    c.close()
    assert len(session._flushed_handlers) == 0
    assert "c1" not in mgr.comms


def test_open_unregisters_if_publish_fails():
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    # Sending on an ended session fails; the comm must not stay registered.
    mgr.active = False
    with pytest.raises(RuntimeError, match="session"):
        comm.ShinyComm(
            comm_id="c1",
            comm_manager=mgr,
            target_name="jupyter.widget",
            session=session,  # type: ignore[arg-type]
            epoch=EPOCH,
        )
    assert "c1" not in mgr.comms


def test_buffers_are_base64_encoded_and_validated(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1",
        comm_manager=mgr,
        target_name="jupyter.widget",
        session=session,  # type: ignore[arg-type]
        epoch=EPOCH,
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    c.send(data={"buffer_paths": [["x"]]}, buffers=[b"\x00\x01"])
    cells = closure_map(session._flushed_handlers[0])
    msg = json.loads(cells["msg_txt"])["msg"]
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


def test_msg_and_close_callbacks():
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(
        comm_id="c1",
        comm_manager=mgr,
        target_name="jupyter.widget",
        session=session,  # type: ignore[arg-type]
        epoch=EPOCH,
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


def test_pending_shiny_comm_close_notifies_once() -> None:
    import shinywidgets._comm as comm

    notified: list[str] = []
    pending = comm.PendingShinyComm("c1", notify_closed=lambda: notified.append("c1"))

    pending.close()
    assert pending.closed is True
    assert notified == ["c1"]

    pending.close()
    assert notified == ["c1"]
