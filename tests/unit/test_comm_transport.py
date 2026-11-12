from __future__ import annotations

import base64
import gc
import json
import weakref
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


def test_orphaned_shiny_comm_methods_are_noops_after_close() -> None:
    import shinywidgets._comm as comm

    orphan = comm.OrphanedShinyComm("c1", pending_open=False)

    assert orphan.send() is None
    assert orphan.close() is None
    assert orphan.on_msg(lambda msg: msg) is None
    assert orphan.take_queued_sends() == []


def test_orphaned_shiny_comm_queues_sends_until_open_or_close() -> None:
    import shinywidgets._comm as comm

    # Pre-open sends queue FIFO; taking them ends the pre-open state
    orphan = comm.OrphanedShinyComm("c1", pending_open=True)
    orphan.send(data={"n": 1})
    orphan.send(data={"n": 2}, metadata={"m": 0})
    queued = [json.loads(msg_txt) for msg_txt in orphan.take_queued_sends()]
    assert [(m["content"]["data"], m["metadata"]) for m in queued] == [
        ({"n": 1}, {}),
        ({"n": 2}, {"m": 0}),
    ]
    assert orphan.take_queued_sends() == []
    # Once the real comm has taken over, sends here are no-ops
    orphan.send(data={"n": 3})
    assert orphan.take_queued_sends() == []

    # Closing a pre-open placeholder drops its queue, and later sends no-op
    closing = comm.OrphanedShinyComm("c2", pending_open=True)
    closing.send(data={"n": 1})
    closing.close()
    closing.send(data={"n": 2})
    assert closing.take_queued_sends() == []

    # A post-close placeholder never queues
    closed = comm.OrphanedShinyComm("c3", pending_open=False)
    closed.send(data={"n": 1})
    assert closed.take_queued_sends() == []


def test_queued_sends_flush_through_the_replacement_comm() -> None:
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    real = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    orphan = comm.OrphanedShinyComm("c1", pending_open=True)
    orphan.send(data={"method": "custom", "data": "first"})
    orphan.send(data={"method": "custom", "data": "second"})
    comm.flush_queued_sends(orphan, real)

    # Both sends scheduled, in order; the queue is empty and stays that way
    assert len(session._flushed_handlers) == 2
    first, second = (
        json.loads(closure_map(fn)["msg_txt"])["content"]["data"]["data"]
        for fn in session._flushed_handlers
    )
    assert (first, second) == ("first", "second")
    assert orphan.take_queued_sends() == []


def test_sends_made_before_the_comm_opens_are_delivered_in_order(
    widget_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    The k3d-style repro: a custom message sent while the widget's output is
    still rendering (its comm is still a placeholder) is no longer dropped.
    """
    import asyncio

    from ipywidgets import IntSlider
    from shiny import reactive
    from shiny.session import session_context
    from shinywidgets._comm import OrphanedShinyComm, ShinyComm

    sent: list[Dict[str, Any]] = []

    async def record(msg_type: str, msg_txt: str) -> None:
        sent.append({"type": msg_type, **json.loads(msg_txt)})

    monkeypatch.setattr(widget_session, "send_custom_message", record)
    loop = asyncio.get_event_loop()

    with session_context(widget_session):
        w = IntSlider(value=1)
        assert isinstance(w.comm, OrphanedShinyComm)
        w.comm.send(data={"method": "custom", "data": "first"})
        w.comm.send(data={"method": "custom", "data": "second"})
        loop.run_until_complete(reactive.flush())
        assert isinstance(w.comm, ShinyComm)
        loop.run_until_complete(widget_session._flushed_callbacks.invoke())

    customs = [
        m["content"]["data"]["data"]
        for m in sent
        if m["type"] == "shinywidgets_comm_msg"
    ]
    assert customs == ["first", "second"]
    w.close()


def test_widget_send_before_comm_open_is_queued(
    widget_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Same repro as above, but through Widget.send() (how k3d's start_auto_play()
    and friends actually send): Widget._send() drops messages whose comm has
    `kernel = None`, so it must be routed onto the placeholder's queue.
    """
    import asyncio

    from ipywidgets import IntSlider
    from shiny import reactive
    from shiny.session import session_context
    from shinywidgets._comm import OrphanedShinyComm, ShinyComm

    sent: list[Dict[str, Any]] = []

    async def record(msg_type: str, msg_txt: str) -> None:
        sent.append({"type": msg_type, **json.loads(msg_txt)})

    monkeypatch.setattr(widget_session, "send_custom_message", record)
    loop = asyncio.get_event_loop()

    with session_context(widget_session):
        w = IntSlider(value=1)
        assert isinstance(w.comm, OrphanedShinyComm)
        w.send({"msg_type": "start_auto_play"})
        w.send({"msg_type": "stop_auto_play"})
        loop.run_until_complete(reactive.flush())
        assert isinstance(w.comm, ShinyComm)
        loop.run_until_complete(widget_session._flushed_callbacks.invoke())

    customs = [
        m["content"]["data"]["content"]["msg_type"]
        for m in sent
        if m["type"] == "shinywidgets_comm_msg"
    ]
    assert customs == ["start_auto_play", "stop_auto_play"]
    w.close()


def test_queued_sends_snapshot_payloads_at_send_time() -> None:
    """
    Like ShinyComm._publish_msg() (which serializes at send time), the queue
    must capture the payload as sent, not as mutated (or buffer-reused) by the
    time the comm opens.
    """
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    real = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    orphan = comm.OrphanedShinyComm("c1", pending_open=True)
    payload: Dict[str, Any] = {"method": "custom", "n": 1}
    buf = bytearray(b"first")
    orphan.send(data=payload, buffers=[buf])
    payload["n"] = 2
    buf[:] = b"secnd"
    orphan.send(data=payload, buffers=[buf])
    comm.flush_queued_sends(orphan, real)

    msgs = [json.loads(closure_map(fn)["msg_txt"]) for fn in session._flushed_handlers]
    assert [m["content"]["data"]["n"] for m in msgs] == [1, 2]
    assert [base64.b64decode(m["buffers"][0]) for m in msgs] == [b"first", b"secnd"]


@pytest.mark.parametrize(
    "make_data",
    [
        lambda: {"method": "custom", "raw": bytearray([1, 2])},
        lambda: {"method": "custom", "samples": (i for i in [1, 2])},
        lambda: {"method": "custom", "raw": b"\x01\x02", "view": memoryview(b"ab")},
    ],
    ids=["bytearray", "generator", "bytes-and-memoryview"],
)
def test_queued_sends_are_serialized_like_direct_sends(make_data: Any) -> None:
    """
    What a send puts on the wire must not depend on whether the comm had
    opened yet: both go through the same serializer.
    """
    import shinywidgets._comm as comm

    session = FakeSession()
    mgr = comm.ShinyCommManager()
    real = comm.ShinyComm(
        comm_id="c1", comm_manager=mgr, target_name="jupyter.widget", session=session
    )
    session._flush_handlers.clear()
    session._flushed_handlers.clear()

    real.send(data=make_data(), buffers=[bytearray(b"buf")])
    orphan = comm.OrphanedShinyComm("c1", pending_open=True)
    orphan.send(data=make_data(), buffers=[bytearray(b"buf")])
    comm.flush_queued_sends(orphan, real)

    direct, queued = (closure_map(fn)["msg_txt"] for fn in session._flushed_handlers)
    assert queued == direct


def test_queued_send_errors_surface_at_the_send() -> None:
    """
    An unsendable payload raises where it was sent (e.g. in the render
    function), not later when the comm opens.
    """
    import shinywidgets._comm as comm

    orphan = comm.OrphanedShinyComm("c1", pending_open=True)
    with pytest.raises(TypeError, match="buffer protocol"):
        orphan.send(data={"method": "custom"}, buffers=[object()])  # type: ignore[list-item]  # deliberately invalid
    with pytest.raises(TypeError, match="not JSON serializable"):
        orphan.send(data={"method": "custom", "bad": object()})
    assert orphan.take_queued_sends() == []


def test_widget_closed_before_its_comm_opened_sends_nothing(
    widget_session, flush_to_browser
) -> None:
    """
    A widget closed before its comm opened never reaches the browser: neither
    its comm_open, nor the sends queued before (or made after) the close.
    """
    from ipywidgets import HTML
    from shiny.session import session_context
    from shinywidgets._shinywidgets import close_widget

    with session_context(widget_session):
        w = HTML(value="pending")
        w.send({"n": 1})
        close_widget(w)
        w.send({"n": 2})

    assert [
        m for m in flush_to_browser() if m["content"]["comm_id"] == w.model_id
    ] == []


@pytest.mark.parametrize("opened", [False, True], ids=["never-opened", "opened"])
def test_closed_widget_is_freed_without_the_cyclic_gc(
    widget_session, flush_to_browser, opened: bool
) -> None:
    """
    Routing a widget's pre-open sends must not tie it into a reference cycle:
    a re-rendered widget (and, e.g., a large figure's data) would then linger
    until the garbage collector's next pass instead of being freed right away.
    """
    from ipywidgets import HTML
    from shiny.session import session_context
    from shinywidgets._shinywidgets import close_widget

    with session_context(widget_session):
        w = HTML(value="x")
        if opened:
            flush_to_browser()
        close_widget(w)
    # Deliver what's pending: scheduled sends hold the comm until then
    flush_to_browser()

    freed = weakref.ref(w)
    gc.collect()
    gc.disable()
    try:
        del w
        assert freed() is None
    finally:
        gc.enable()


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
