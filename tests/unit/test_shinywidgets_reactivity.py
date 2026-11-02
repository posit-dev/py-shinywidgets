import asyncio
import gc

import pytest
import shinywidgets._accessors as acc
import shinywidgets._shinywidgets as sw


class FakeContext:
    def __init__(self) -> None:
        self.invalidated = 0
        self._on_invalidate = []

    def invalidate(self) -> None:
        self.invalidated += 1

    def on_invalidate(self, fn):  # type: ignore[no-untyped-def]
        self._on_invalidate.append(fn)
        return fn

    def run_invalidate_callbacks(self) -> None:
        for fn in list(self._on_invalidate):
            fn()


class FakeWidget:
    def __init__(self, traits: dict[str, object]) -> None:
        self._traits = set(traits.keys())
        for k, v in traits.items():
            setattr(self, k, v)

        self.observe_calls = []
        self.unobserve_calls = []

    def has_trait(self, name: str) -> bool:
        return name in self._traits

    def observe(self, handler, names, type):  # type: ignore[no-untyped-def]
        self.observe_calls.append((handler, list(names), type))

    def unobserve(self, handler, names, type):  # type: ignore[no-untyped-def]
        self.unobserve_calls.append((handler, list(names), type))


def test_reactive_depend_outside_context_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        sw, "get_current_context", lambda: (_ for _ in ()).throw(RuntimeError())
    )
    w = FakeWidget({"x": 1})

    with pytest.raises(
        RuntimeError,
        match=r"reactive_read\(\) must be called within a reactive context",
    ):
        sw.reactive_depend(w, "x")  # type: ignore[arg-type]


def test_reactive_read_outside_context_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        sw, "get_current_context", lambda: (_ for _ in ()).throw(RuntimeError())
    )
    w = FakeWidget({"x": 1})

    with pytest.raises(
        RuntimeError,
        match=r"reactive_read\(\) must be called within a reactive context",
    ):
        sw.reactive_read(w, "x")  # type: ignore[arg-type]


def test_reactive_depend_validates_trait_existence(monkeypatch) -> None:
    ctx = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: ctx)
    w = FakeWidget({"ok": 1})

    with pytest.raises(ValueError) as excinfo:
        sw.reactive_depend(w, "nope")  # type: ignore[arg-type]

    msg = str(excinfo.value)
    assert "nope" in msg
    assert "FakeWidget" in msg


def test_reactive_depend_observe_and_cleanup_wiring(monkeypatch) -> None:
    ctx = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: ctx)
    w = FakeWidget({"a": 1, "b": 2})

    sw.reactive_depend(w, ["a", "b"], type="change")  # type: ignore[arg-type]

    assert len(w.observe_calls) == 1
    handler, names, typ = w.observe_calls[0]
    assert names == ["a", "b"]
    assert typ == "change"

    handler(change={})
    assert ctx.invalidated == 1

    ctx.run_invalidate_callbacks()

    assert len(w.unobserve_calls) == 1
    uhandler, unames, utyp = w.unobserve_calls[0]
    assert uhandler is handler
    assert unames == ["a", "b"]
    assert utyp == "change"


def test_reactive_read_returns_values_in_order(monkeypatch) -> None:
    ctx = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: ctx)
    w = FakeWidget({"a": 1, "b": 2})

    assert sw.reactive_read(w, "a") == 1  # type: ignore[arg-type]
    assert sw.reactive_read(w, ["a", "b"]) == (1, 2)  # type: ignore[arg-type]


def test_reactive_depend_unlimited_without_policy(monkeypatch) -> None:
    ctx = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: ctx)
    w = FakeWidget({"x": 1})
    sw.reactive_depend(w, "x")  # type: ignore[arg-type]
    handler = w.observe_calls[0][0]
    handler({})
    handler({})
    assert ctx.invalidated == 2


class FakeTimers:
    def __init__(self) -> None:
        self.timers: list = []

    def __call__(self, delay, fn):  # type: ignore[no-untyped-def]
        entry = (delay, fn)
        self.timers.append(entry)
        return lambda: self.timers.remove(entry) if entry in self.timers else None

    def fire(self) -> None:
        pending, self.timers = self.timers, []
        for _, fn in pending:
            fn()


def test_reactive_depend_debounces_when_renderer_registered_policy(
    monkeypatch,
) -> None:
    timers = FakeTimers()
    monkeypatch.setattr(acc, "timer_schedule", timers)
    ctx = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: ctx)
    w = FakeWidget({"x": 1})
    acc.register_rate_policy(w, "debounce", 0.1)  # type: ignore[arg-type]
    sw.reactive_depend(w, "x")  # type: ignore[arg-type]
    handler = w.observe_calls[0][0]
    handler({})
    handler({})
    assert ctx.invalidated == 0 and len(timers.timers) == 1
    assert timers.timers[0][0] == 0.1
    timers.fire()
    assert ctx.invalidated == 1

    # A context invalidated some other way isn't invalidated again later.
    handler({})
    ctx.run_invalidate_callbacks()
    timers.fire()
    assert ctx.invalidated == 1


def test_reactive_depend_throttle_window_spans_reruns(monkeypatch) -> None:
    timers = FakeTimers()
    monkeypatch.setattr(acc, "timer_schedule", timers)
    w = FakeWidget({"x": 1})
    acc.register_rate_policy(w, "throttle", 1)  # type: ignore[arg-type]

    first = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: first)
    sw.reactive_depend(w, "x")  # type: ignore[arg-type]
    w.observe_calls[-1][0]({})
    assert first.invalidated == 1  # leading edge
    first.run_invalidate_callbacks()

    # The reader re-runs and depends again, inside the same window
    second = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: second)
    sw.reactive_depend(w, "x")  # type: ignore[arg-type]
    w.observe_calls[-1][0]({})
    w.observe_calls[-1][0]({})
    assert second.invalidated == 0
    timers.fire()  # the window closes
    assert second.invalidated == 1


class IdleSession:
    """A session whose idle queue runs only when drained (never, if it ended)."""

    def __init__(self) -> None:
        self.queued: list = []

    def is_stub_session(self) -> bool:
        return False

    def root_scope(self) -> "IdleSession":
        return self

    def run_once_when_idle(self, fn) -> None:  # type: ignore[no-untyped-def]
        self.queued.append(fn)

    def drain(self) -> None:
        queued, self.queued = self.queued, []
        for fn in queued:
            fn()


def test_throttle_survives_the_session_that_opened_its_window_ending(
    monkeypatch,
) -> None:
    # A shared widget: a change from one session opens the window, then that
    # session disconnects (its idle queue never runs again)
    reader_session, ended_session = IdleSession(), IdleSession()
    current = {"session": reader_session}
    monkeypatch.setattr(sw, "get_current_session", lambda: current["session"])
    monkeypatch.setattr(acc, "get_current_session", lambda: current["session"])
    w = FakeWidget({"x": 1})
    acc.register_rate_policy(w, "throttle", 0.01)  # type: ignore[arg-type]

    def depend() -> FakeContext:
        ctx = FakeContext()
        monkeypatch.setattr(sw, "get_current_context", lambda: ctx)
        current["session"] = reader_session
        sw.reactive_depend(w, "x")  # type: ignore[arg-type]
        return ctx

    def change() -> None:
        current["session"] = ended_session
        w.observe_calls[-1][0]({})

    async def main() -> None:
        first = depend()
        change()
        assert first.invalidated == 1  # leading edge
        first.run_invalidate_callbacks()
        second = depend()
        change()  # inside the window
        await asyncio.sleep(0.05)
        reader_session.drain()
        assert second.invalidated == 1  # the window closed anyway
        second.run_invalidate_callbacks()
        third = depend()
        change()
        assert third.invalidated == 1  # and a new one opens

    asyncio.run(main())


class UnhashableWidget(FakeWidget):
    # Like plotly's FigureWidget, which defines __eq__ without __hash__
    def __eq__(self, other: object) -> bool:
        return self is other

    __hash__ = None  # type: ignore[assignment]


def test_register_policy_for_unhashable_widget() -> None:
    w = UnhashableWidget({})
    acc.register_rate_policy(w, "throttle", 0.05)  # type: ignore[arg-type]
    rate = acc.rate_policy_for(w)  # type: ignore[arg-type]
    assert rate is not None and (rate.policy, rate.delay) == ("throttle", 0.05)
    assert acc.rate_policy_for(UnhashableWidget({})) is None  # type: ignore[arg-type]


def test_register_none_removes_policy() -> None:
    w = FakeWidget({})
    acc.register_rate_policy(w, "debounce", None)  # type: ignore[arg-type]
    rate = acc.rate_policy_for(w)  # type: ignore[arg-type]
    assert rate is not None and (rate.policy, rate.delay) == ("debounce", 0.25)
    acc.register_rate_policy(w, None, None)  # type: ignore[arg-type]
    assert acc.rate_policy_for(w) is None  # type: ignore[arg-type]


def test_policy_is_forgotten_with_the_widget() -> None:

    w = FakeWidget({})
    acc.register_rate_policy(w, "debounce", 0.1)  # type: ignore[arg-type]
    key = id(w)
    assert key in acc.RATE_POLICIES
    del w
    gc.collect()
    assert key not in acc.RATE_POLICIES
