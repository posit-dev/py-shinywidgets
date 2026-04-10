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


@pytest.fixture(autouse=True)
def _reset_comm_manager_class_state() -> None:
    from shinywidgets._comm import ShinyCommManager

    ShinyCommManager.comms.clear()


def _scheduled_payloads(session: FakeSession):
    return {
        "flush": list(session._flush_handlers),
        "flushed": list(session._flushed_handlers),
    }


def test_open_registers_and_schedules_on_flush(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    _ = comm.ShinyComm(
        comm_id="c1",
        comm_manager=mgr,
        target_name="jupyter.widgets",
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
    assert msg["content"]["target_name"] == "jupyter.widgets"
    assert msg["content"]["target_module"] is None
    assert msg["buffers"] == []
    assert msg["ident"] == "comm-c1"


def test_send_schedules_on_flushed(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widgets")
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
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widgets")
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    c.close()
    assert "c1" not in mgr.comms

    # Second close is a no-op (does not schedule a second message).
    n = len(session._flushed_handlers)
    c.close()
    assert len(session._flushed_handlers) == n


def test_close_does_not_publish_without_session(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widgets")
    session._flushed_handlers.clear()

    # Simulate leaving session context before closing.
    monkeypatch.setattr(comm, "get_current_session", lambda: None)
    c.close()
    assert len(session._flushed_handlers) == 0


def test_open_unregisters_if_publish_fails(monkeypatch):
    import shinywidgets._comm as comm

    # Force publish to fail by returning no session.
    monkeypatch.setattr(comm, "get_current_session", lambda: None)

    mgr = comm.ShinyCommManager()
    with pytest.raises(RuntimeError):
        comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widgets")
    assert "c1" not in mgr.comms


def test_buffers_are_base64_encoded_and_validated(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widgets")
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
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widgets")

    seen: Dict[str, Any] = {"msg": None, "close": None}
    c.on_msg(lambda m: seen.__setitem__("msg", m))
    c.on_close(lambda m: seen.__setitem__("close", m))

    c.handle_msg({"hello": "world"})
    c.handle_close({"bye": "world"})
    assert seen["msg"] == {"hello": "world"}
    assert seen["close"] == {"bye": "world"}
