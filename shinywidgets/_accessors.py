from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional, Tuple

RatePolicy = Literal["debounce", "throttle"]

# (delay in seconds, fn) -> cancel
Schedule = Callable[[float, Callable[[], None]], Callable[[], None]]

Emit = Callable[[object], None]

# (widget, emit) -> detach. The widget is typed Any so that each attach can
# annotate the concrete widget class it expects (Callable params are
# contravariant, so `Callable[[Widget, ...], ...]` would reject those).
Attach = Callable[[Any, Emit], Callable[[], None]]


def identity(x: object) -> object:
    return x


def never_ready_check(raw: object) -> bool:
    return False


@dataclass(frozen=True)
class AccessorSpec:
    """
    Declares one accessor on a renderer.

    Parameters
    ----------
    name
        The renderer method's name.
    kind
        "state" mirrors something the widget always has (it is never reset);
        "event" reports something that happened, and resets to `None` on
        re-render.
    attach
        Registers the library hook on a freshly rendered widget, calling `emit`
        with each raw value, and returns a function that removes the hook.
    payload
        Builds the user-facing value from a raw one; runs lazily, once per
        published raw value.
    priority
        "input" ignores a raw value equal to the previous one; "event"
        re-publishes it (so repeated identical clicks each fire).
    rate_policy, rate_delay
        Default rate limit (`rate_delay` in milliseconds), overridable by the
        renderer's kwargs.
    clears
        Names of accessors reset to `None` whenever this one publishes.
    eager
        Attach during render rather than on first read, for widgets whose
        events are lost unless a handler exists before the view is created.
    not_ready
        True for raw values that mean "the widget hasn't reported yet"; reads
        then cancel (`req(False)`) instead of returning a value.
    """

    name: str
    kind: Literal["state", "event"]
    attach: Attach
    payload: Callable[[Any], object] = identity
    priority: Literal["input", "event"] = "input"
    rate_policy: Optional[RatePolicy] = None
    rate_delay: int = 250
    clears: Tuple[str, ...] = ()
    eager: bool = False
    not_ready: Callable[[Any], bool] = never_ready_check

    def __post_init__(self) -> None:
        if self.name == "value":
            raise ValueError(
                "An accessor can't be named `value`: renderers already use it for the rendered object."
            )
        if self.name.startswith("_"):
            raise ValueError(
                f"Accessor name {self.name!r} can't start with an underscore."
            )


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


def payloads_equal(a: object, b: object) -> bool:
    if a is b:
        return True
    try:
        return bool(a == b)
    except (ValueError, TypeError):
        # Array-likes (numpy, pandas) compare elementwise, and their truth
        # value is ambiguous.
        pass
    # numpy is optional, so import it only once a payload needs it.
    try:
        import numpy as np
    except ImportError:
        return False

    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        return bool(np.array_equal(a, b))
    return False
