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
        target_name="jupyter.widget",
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
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")
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
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")
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
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")
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
        comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")
    assert "c1" not in mgr.comms


def test_buffers_are_base64_encoded_and_validated(monkeypatch):
    import shinywidgets._comm as comm

    session = FakeSession()
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")
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
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")

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
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")
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
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")
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
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")
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
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")
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
    monkeypatch.setattr(comm, "get_current_session", lambda: session)

    mgr = comm.ShinyCommManager()
    c1 = comm.ShinyComm(comm_id="c1", comm_manager=mgr, target_name="jupyter.widget")
    c2 = comm.ShinyComm(comm_id="c2", comm_manager=mgr, target_name="jupyter.widget")
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
