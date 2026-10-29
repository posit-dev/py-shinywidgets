from __future__ import annotations

import asyncio
from typing import Any, Callable, List, Optional, Tuple, cast

import pytest
import shinywidgets._accessors as acc


class FakeSchedule:
    def __init__(self) -> None:
        self.timers: List[Tuple[float, Callable[[], None]]] = []

    def __call__(self, delay: float, fn: Callable[[], None]) -> Callable[[], None]:
        entry = (delay, fn)
        self.timers.append(entry)

        def cancel() -> None:
            if entry in self.timers:
                self.timers.remove(entry)

        return cancel

    def fire(self) -> None:
        pending, self.timers = self.timers, []
        for _, fn in pending:
            fn()


def test_no_policy_calls_immediately() -> None:
    calls: List[int] = []
    rl = acc.RateLimiter(
        lambda: calls.append(1), policy=None, delay_ms=250, schedule=FakeSchedule()
    )
    rl.call()
    rl.call()
    assert calls == [1, 1]


def test_zero_delay_disables_policy() -> None:
    calls: List[int] = []
    s = FakeSchedule()
    rl = acc.RateLimiter(
        lambda: calls.append(1), policy="debounce", delay_ms=0, schedule=s
    )
    rl.call()
    assert calls == [1] and s.timers == []


def test_debounce_is_trailing_only() -> None:
    calls: List[int] = []
    s = FakeSchedule()
    rl = acc.RateLimiter(
        lambda: calls.append(1), policy="debounce", delay_ms=250, schedule=s
    )
    rl.call()
    rl.call()
    rl.call()
    assert calls == [] and len(s.timers) == 1 and s.timers[0][0] == 0.25
    s.fire()
    assert calls == [1]


def test_throttle_is_leading_and_trailing() -> None:
    calls: List[int] = []
    s = FakeSchedule()
    rl = acc.RateLimiter(
        lambda: calls.append(1), policy="throttle", delay_ms=100, schedule=s
    )
    rl.call()
    assert calls == [1] and len(s.timers) == 1
    rl.call()
    rl.call()
    assert calls == [1]
    s.fire()
    assert calls == [1, 1] and len(s.timers) == 1  # trailing call opened a new window
    s.fire()
    assert calls == [1, 1] and s.timers == []  # quiet window closes with nothing to do


def test_cancel_drops_pending_timer() -> None:
    calls: List[int] = []
    s = FakeSchedule()
    rl = acc.RateLimiter(
        lambda: calls.append(1), policy="debounce", delay_ms=250, schedule=s
    )
    rl.call()
    rl.cancel()
    assert s.timers == []
    s.fire()
    assert calls == []


def noop_attach(widget: object, emit: Callable[[object], None]) -> Callable[[], None]:
    return lambda: None


def test_spec_rejects_reserved_names() -> None:
    with pytest.raises(ValueError, match="value"):
        acc.AccessorSpec(name="value", kind="state", attach=noop_attach)
    with pytest.raises(ValueError, match="underscore"):
        acc.AccessorSpec(name="_x", kind="state", attach=noop_attach)


def test_payloads_equal_plain_and_identity() -> None:
    assert acc.payloads_equal({"a": 1}, {"a": 1})
    assert not acc.payloads_equal({"a": 1}, {"a": 2})
    x = object()
    assert acc.payloads_equal(x, x)


def test_payloads_equal_tolerates_array_payloads() -> None:
    np = pytest.importorskip("numpy")
    assert acc.payloads_equal(np.array([1, 2]), np.array([1, 2]))
    assert not acc.payloads_equal(np.array([1, 2]), np.array([1, 3]))
    assert not acc.payloads_equal(np.array([1, 2]), [1, 2])


class Capture:
    def __init__(self) -> None:
        self.emit: Optional[Callable[[object], None]] = None
        self.attached = 0
        self.detached = 0

    def attach(
        self, widget: object, emit: Callable[[object], None]
    ) -> Callable[[], None]:
        self.emit = emit
        self.attached += 1

        def detach() -> None:
            self.detached += 1

        return detach

    def send(self, raw: object) -> None:
        assert self.emit is not None
        self.emit(raw)


class Cancel(Exception):
    pass


def raise_cancel(*args: object) -> None:
    raise Cancel()


def make(
    **spec_kwargs: Any,
) -> Tuple[acc.Accessors, Capture, FakeSchedule]:
    acc_kwargs = {
        k: spec_kwargs.pop(k)
        for k in ("override_policy", "override_delay")
        if k in spec_kwargs
    }
    cap = Capture()
    spec = acc.AccessorSpec(
        name="clicked", kind="event", attach=cap.attach, **spec_kwargs
    )
    s = FakeSchedule()
    a = acc.Accessors(
        [spec],
        rate_policy=acc_kwargs.get("override_policy"),
        rate_delay=acc_kwargs.get("override_delay"),
        schedule=s,
    )
    return a, cap, s


def spy_sets(a: acc.Accessors, name: str) -> List[object]:
    sets: List[object] = []
    value = a.values[name]
    original = value.set

    def spy(v: acc.Box) -> bool:
        sets.append(v.raw)
        return original(v)

    value.set = spy  # type: ignore[method-assign]  # spy on publishes
    return sets


def test_read_before_render_cancels(monkeypatch: pytest.MonkeyPatch) -> None:
    a, _, _ = make()
    monkeypatch.setattr(acc, "req", raise_cancel)
    with pytest.raises(Cancel):
        a.read("clicked")


def test_read_unknown_name_raises() -> None:
    a, _, _ = make()
    with pytest.raises(KeyError):
        a.read("nope")


def test_lazy_attach_on_first_read_then_every_render() -> None:
    a, cap, _ = make()
    a.on_render(object())
    assert cap.attached == 0
    assert a.read("clicked") is None
    assert cap.attached == 1
    a.on_render(object())
    assert cap.detached == 1 and cap.attached == 2


def test_eager_attach_in_on_render() -> None:
    a, cap, _ = make(eager=True)
    a.on_render(object())
    assert cap.attached == 1


def test_event_publishes_and_resets_on_render() -> None:
    a, cap, _ = make()
    a.on_render(object())
    a.read("clicked")
    cap.send({"x": 1})
    assert a.read("clicked") == {"x": 1}
    a.on_render(object())
    assert a.read("clicked") is None


def test_input_priority_ignores_equal_payloads() -> None:
    a, cap, _ = make()
    a.on_render(object())
    a.read("clicked")
    sets = spy_sets(a, "clicked")
    cap.send({"x": 1})
    cap.send({"x": 1})
    cap.send({"x": 2})
    assert sets == [{"x": 1}, {"x": 2}]


def test_event_priority_republishes_equal_payloads() -> None:
    a, cap, _ = make(priority="event")
    a.on_render(object())
    a.read("clicked")
    sets = spy_sets(a, "clicked")
    same = {"x": 1}
    cap.send(same)
    cap.send(same)
    assert len(sets) == 2


def test_input_priority_tolerates_array_payloads() -> None:
    np = pytest.importorskip("numpy")
    a, cap, _ = make()
    a.on_render(object())
    a.read("clicked")
    cap.send(np.array([1, 2]))
    cap.send(np.array([1, 2]))
    assert list(cast(Any, a.read("clicked"))) == [1, 2]


def test_debounced_stream_publishes_latest_raw() -> None:
    a, cap, s = make(rate_policy="debounce")
    a.on_render(object())
    a.read("clicked")
    cap.send({"x": 1})
    assert a.read("clicked") is None and len(s.timers) == 1
    cap.send({"x": 2})
    s.fire()
    assert a.read("clicked") == {"x": 2}


def test_zero_delay_override_disables_default_policy() -> None:
    a, cap, s = make(rate_policy="debounce", override_delay=0)
    a.on_render(object())
    a.read("clicked")
    cap.send({"x": 1})
    assert a.read("clicked") == {"x": 1} and s.timers == []


def test_override_policy_and_delay_apply_to_specs_with_a_default() -> None:
    a, cap, s = make(
        rate_policy="debounce", override_policy="throttle", override_delay=100
    )
    a.on_render(object())
    a.read("clicked")
    cap.send({"x": 1})
    assert a.read("clicked") == {"x": 1}  # throttle's leading edge
    assert s.timers[0][0] == 0.1


def test_override_policy_ignored_without_a_default() -> None:
    a, cap, s = make(override_policy="debounce")
    a.on_render(object())
    a.read("clicked")
    cap.send({"x": 1})
    assert a.read("clicked") == {"x": 1} and s.timers == []


def test_stale_generation_is_ignored() -> None:
    a, cap, s = make(rate_policy="debounce")
    a.on_render(object())
    a.read("clicked")
    stale_emit = cap.emit
    assert stale_emit is not None
    cap.send({"x": 1})
    a.on_render(object())  # re-render while the timer is pending
    s.fire()
    assert a.read("clicked") is None
    stale_emit({"x": 2})  # a handler the old widget failed to remove
    s.fire()
    assert a.read("clicked") is None


def test_emitting_none_clears_and_the_same_value_refires() -> None:
    a, cap, _ = make()
    a.on_render(object())
    a.read("clicked")
    cap.send({"x": 1})
    cap.send(None)  # e.g. plotly's double-click
    assert a.read("clicked") is None
    # Clicking the same point again after a clear is a change.
    cap.send({"x": 1})
    assert a.read("clicked") == {"x": 1}


def test_render_without_widget_does_not_reattach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a, cap, _ = make()
    a.on_render(object())
    a.read("clicked")
    a.on_render(None)  # the render function returned None
    assert cap.attached == 1
    monkeypatch.setattr(acc, "req", raise_cancel)
    with pytest.raises(Cancel):
        a.read("clicked")


class StateWidget:
    def __init__(self, current: object) -> None:
        self.current = current


def test_rerender_while_debouncing_publishes_the_new_widgets_state() -> None:
    emits: List[Callable[[object], None]] = []

    def attach(
        widget: StateWidget, emit: Callable[[object], None]
    ) -> Callable[[], None]:
        emits.append(emit)
        emit(widget.current)
        return lambda: None

    spec = acc.AccessorSpec(
        name="sel", kind="state", attach=attach, rate_policy="debounce"
    )
    s = FakeSchedule()
    a = acc.Accessors([spec], schedule=s)
    a.on_render(StateWidget("empty"))
    assert a.read("sel") == "empty"
    emits[-1]("brush")
    s.fire()
    assert a.read("sel") == "brush"
    emits[-1]("empty")  # the user clears the brush; still debouncing
    a.on_render(StateWidget("empty"))  # re-render before the timer fires
    assert a.read("sel") == "empty"


def test_state_is_kept_across_renders() -> None:
    cap = Capture()
    spec = acc.AccessorSpec(name="zoom", kind="state", attach=cap.attach)
    a = acc.Accessors([spec], schedule=FakeSchedule())
    a.on_render(object())
    a.read("zoom")
    cap.send(3)
    a.on_render(object())
    assert a.read("zoom") == 3


def test_not_ready_cancels(monkeypatch: pytest.MonkeyPatch) -> None:
    cap = Capture()
    spec = acc.AccessorSpec(
        name="bounds", kind="state", attach=cap.attach, not_ready=lambda raw: raw == ()
    )
    a = acc.Accessors([spec], schedule=FakeSchedule())
    a.on_render(object())
    monkeypatch.setattr(acc, "req", raise_cancel)
    a.read("bounds")  # attaches; nothing reported yet is None, not the sentinel
    cap.send(())
    with pytest.raises(Cancel):
        a.read("bounds")
    cap.send(((0, 0), (1, 1)))
    assert a.read("bounds") == ((0, 0), (1, 1))


def test_close_detaches_and_cancels() -> None:
    a, cap, s = make(rate_policy="debounce")
    a.on_render(object())
    a.read("clicked")
    cap.send({"x": 1})
    a.close()
    a.close()
    assert cap.detached == 1 and s.timers == []


def test_payload_is_memoised_per_publish() -> None:
    cap = Capture()
    builds: List[object] = []

    def build(raw: object) -> object:
        builds.append(raw)
        return {"built": raw}

    spec = acc.AccessorSpec(name="pts", kind="event", attach=cap.attach, payload=build)
    a = acc.Accessors([spec], schedule=FakeSchedule())
    a.on_render(object())
    a.read("pts")
    cap.send(1)
    assert a.read("pts") == {"built": 1}
    a.read("pts")
    assert builds == [1]
    cap.send(2)
    assert a.read("pts") == {"built": 2} and builds == [1, 2]


def test_read_raw_skips_payload() -> None:
    cap = Capture()
    spec = acc.AccessorSpec(
        name="pts", kind="event", attach=cap.attach, payload=lambda raw: {"built": raw}
    )
    a = acc.Accessors([spec], schedule=FakeSchedule())
    a.on_render(object())
    a.read("pts")
    cap.send([1])
    assert a.read("pts", raw=True) == [1]


def test_value_emitted_during_attach_skips_rate_limit() -> None:
    def attach(widget: object, emit: Callable[[object], None]) -> Callable[[], None]:
        emit("initial")
        return lambda: None

    spec = acc.AccessorSpec(
        name="sel", kind="state", attach=attach, rate_policy="debounce"
    )
    s = FakeSchedule()
    a = acc.Accessors([spec], schedule=s)
    a.on_render(object())
    assert a.read("sel") == "initial" and s.timers == []


def test_failed_attach_is_not_retried_on_render() -> None:
    calls: List[int] = []

    def attach(widget: object, emit: Callable[[object], None]) -> Callable[[], None]:
        calls.append(1)
        raise TypeError("unsupported layout")

    a = acc.Accessors(
        [acc.AccessorSpec(name="sel", kind="event", attach=attach)],
        schedule=FakeSchedule(),
    )
    a.on_render(object())
    with pytest.raises(TypeError):
        a.read("sel")
    a.on_render(object())  # must not raise from inside a render
    assert calls == [1]


class IdleSession:
    def __init__(self) -> None:
        self.queued: List[Callable[[], object]] = []

    def is_stub_session(self) -> bool:
        return False

    def root_scope(self) -> "IdleSession":
        return self

    def run_once_when_idle(self, fn: Callable[[], object]) -> None:
        self.queued.append(fn)


def test_loop_schedule_runs_through_the_sessions_idle_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = IdleSession()
    monkeypatch.setattr(acc, "get_current_session", lambda: session)
    calls: List[int] = []

    async def main() -> None:
        acc.loop_schedule(0, lambda: calls.append(1))
        await asyncio.sleep(0.01)

    asyncio.run(main())
    # Reactive state changes at the start of a cycle, as py-shiny requires
    # for changes made outside one
    assert calls == [] and len(session.queued) == 1
    session.queued[0]()
    assert calls == [1]


def test_loop_schedule_cancel_also_drops_a_queued_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = IdleSession()
    monkeypatch.setattr(acc, "get_current_session", lambda: session)
    calls: List[int] = []

    async def main() -> Callable[[], None]:
        cancel = acc.loop_schedule(0, lambda: calls.append(1))
        await asyncio.sleep(0.01)
        return cancel

    cancel = asyncio.run(main())
    cancel()  # e.g. a re-render between the timer and the next cycle
    session.queued[0]()
    assert calls == []
