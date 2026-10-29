from __future__ import annotations

from typing import Callable, List, Tuple

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
