from __future__ import annotations

import asyncio
import base64
import json
from typing import Any, Awaitable, Callable, Dict, List, Optional

import pytest
from shiny import App, Session, reactive, ui
from shiny._connection import MockConnection
from shiny.reactive import _core as reactive_core
from shinywidgets._comm import ShinyComm, ShinyCommManager

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


# ---------------------------------------------------------------------------
# Delivery of messages published outside a reactive flush. These run a real
# Shiny session (on a MockConnection) so that sends only happen when Shiny
# itself would flush.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fresh_reactive_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    # Shiny's reactive lock is process-global and binds to the first event
    # loop that contends it, but each test here runs its own loop.
    monkeypatch.setattr(reactive_core._reactive_environment, "_lock", None)


class RecordingConnection(MockConnection):
    def __init__(self) -> None:
        super().__init__()
        self.sent: List[Dict[str, Any]] = []

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    def custom_types(self) -> List[str]:
        return [t for m in self.sent for t in m.get("custom", {})]

    def flush_count(self) -> int:
        return sum("values" in m for m in self.sent)


def run_with_session(
    test: Callable[[Session, RecordingConnection], Awaitable[None]],
) -> None:
    async def main() -> None:
        conn = RecordingConnection()
        session = App(ui.page_fluid(), None)._create_session(conn)
        run = asyncio.create_task(session._run())
        conn.cause_receive(json.dumps({"method": "init", "data": {}}))
        assert await wait_for(lambda: conn.flush_count() > 0)
        try:
            await test(session, conn)
        finally:
            conn.cause_disconnect()
            await run

    asyncio.run(main())


async def wait_for(cond: Callable[[], bool], timeout: float = 1.0) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not cond():
        if loop.time() > deadline:
            return False
        await asyncio.sleep(0.01)
    return True


def open_comm(
    session: Session, manager: Optional[ShinyCommManager] = None
) -> ShinyComm:
    return ShinyComm(
        comm_id="c1",
        comm_manager=manager or ShinyCommManager(),
        target_name="jupyter.widget",
        session=session,
    )


def test_messages_published_outside_a_flush_are_delivered():
    async def test(session: Session, conn: RecordingConnection) -> None:
        c = open_comm(session)
        c.send(data={"x": 1})
        assert await wait_for(lambda: len(conn.custom_types()) == 2)
        assert conn.custom_types() == [
            "shinywidgets_comm_open",
            "shinywidgets_comm_msg",
        ]

    run_with_session(test)


def test_messages_published_from_another_thread_are_delivered():
    async def test(session: Session, conn: RecordingConnection) -> None:
        c = open_comm(session)
        await asyncio.to_thread(c.send, data={"x": 1})
        assert await wait_for(lambda: len(conn.custom_types()) == 2)
        assert conn.custom_types() == [
            "shinywidgets_comm_open",
            "shinywidgets_comm_msg",
        ]

    run_with_session(test)


def test_messages_published_during_a_flush_are_sent_by_that_flush():
    async def test(session: Session, conn: RecordingConnection) -> None:
        n_flushes = conn.flush_count()
        # Holding the lock is what Shiny does while handling client input
        # (which always ends with a flush).
        async with reactive.lock():
            c = open_comm(session)
            c.send(data={"x": 1})
            flush_tasks = set(c.comm_manager.flush_tasks)
            assert len(flush_tasks) == 1
            await asyncio.sleep(0.05)
            assert conn.custom_types() == []
            await reactive.flush()
        assert conn.custom_types() == [
            "shinywidgets_comm_open",
            "shinywidgets_comm_msg",
        ]
        # The requested flush runs (without error), sees there's nothing left
        # to deliver, and skips flushing again.
        await asyncio.gather(*flush_tasks)
        assert conn.flush_count() == n_flushes + 1

    run_with_session(test)


def test_messages_published_late_in_a_flush_are_delivered():
    async def test(session: Session, conn: RecordingConnection) -> None:
        c = open_comm(session)
        assert await wait_for(lambda: len(conn.custom_types()) == 1)
        # A message published while the session is already running its
        # on_flushed callbacks misses that flush.
        session.on_flushed(lambda: c.send(data={"x": 1}))
        async with reactive.lock():
            await reactive.flush()
        assert await wait_for(lambda: len(conn.custom_types()) == 2)

    run_with_session(test)


def test_no_flush_is_requested_after_the_session_ended():
    async def test(session: Session, conn: RecordingConnection) -> None:
        c = open_comm(session)
        assert await wait_for(lambda: len(conn.custom_types()) == 1)
        n_flushes = conn.flush_count()
        c.comm_manager.active = False
        c.send(data={"x": 1})
        await asyncio.sleep(0.05)
        assert conn.flush_count() == n_flushes

    run_with_session(test)


def test_manager_created_off_the_loop_adopts_it_when_publishing():
    manager = ShinyCommManager()
    assert manager.loop is None

    async def test(session: Session, conn: RecordingConnection) -> None:
        c = open_comm(session, manager)
        c.send(data={"x": 1})
        assert await wait_for(lambda: len(conn.custom_types()) == 2)

    run_with_session(test)
