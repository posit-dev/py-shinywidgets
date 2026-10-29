from __future__ import annotations

import asyncio
from typing import Callable, Literal, Optional

RatePolicy = Literal["debounce", "throttle"]

# (delay in seconds, fn) -> cancel
Schedule = Callable[[float, Callable[[], None]], Callable[[], None]]


class RateLimiter:
    """
    Runs `fn` on `call()`, immediately or rate-limited. Debounce is
    trailing-only; throttle runs on the leading edge and once more when the
    window closes if calls arrived inside it.
    """

    def __init__(
        self,
        fn: Callable[[], None],
        *,
        policy: Optional[RatePolicy],
        delay_ms: int,
        schedule: Optional[Schedule] = None,
    ) -> None:
        self._fn = fn
        self._policy = policy if delay_ms > 0 else None
        self._delay = delay_ms / 1000
        self._schedule = schedule or loop_schedule
        self._cancel_timer: Optional[Callable[[], None]] = None
        self._pending = False

    def call(self) -> None:
        if self._policy is None:
            self._fn()
        elif self._policy == "debounce":
            self.cancel()
            self._cancel_timer = self._schedule(self._delay, self._debounce_fire)
        elif self._cancel_timer is None:
            self._fn()
            self._open_window()
        else:
            self._pending = True

    def cancel(self) -> None:
        if self._cancel_timer is not None:
            self._cancel_timer()
            self._cancel_timer = None
        self._pending = False

    def _debounce_fire(self) -> None:
        self._cancel_timer = None
        self._fn()

    def _open_window(self) -> None:
        self._cancel_timer = self._schedule(self._delay, self._close_window)

    def _close_window(self) -> None:
        self._cancel_timer = None
        if self._pending:
            self._pending = False
            self._fn()
            self._open_window()


def loop_schedule(delay: float, fn: Callable[[], None]) -> Callable[[], None]:
    handle = asyncio.get_running_loop().call_later(delay, fn)
    return handle.cancel
