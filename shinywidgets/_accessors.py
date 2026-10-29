from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, Literal, Optional, Sequence, Tuple
from weakref import WeakKeyDictionary

from shiny import reactive, req
from shiny.reactive._core import (
    get_current_context,  # pyright: ignore[reportPrivateImportUsage]
)

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


# The rate policy each renderer asked for, applied to `reactive_read()` on
# its widget.
RATE_POLICIES: WeakKeyDictionary[object, Tuple[RatePolicy, int]] = WeakKeyDictionary()


def register_rate_policy(
    widget: object, policy: Optional[RatePolicy], delay_ms: Optional[int]
) -> None:
    if policy is None:
        RATE_POLICIES.pop(widget, None)
    else:
        RATE_POLICIES[widget] = (policy, 250 if delay_ms is None else delay_ms)


def rate_policy_for(widget: object) -> Optional[Tuple[RatePolicy, int]]:
    return RATE_POLICIES.get(widget)


@dataclass
class Box:
    """
    Wraps each published raw value. `reactive.Value.set()` ignores a value
    identical to the current one, and event-priority accessors must re-fire
    on identical raws, so every publish stores a fresh box.
    """

    raw: object


class Accessors:
    """
    The runtime behind one renderer's accessors: one `reactive.Value` per
    accessor, attached to each newly rendered widget.
    """

    def __init__(
        self,
        specs: Sequence[AccessorSpec],
        *,
        rate_policy: Optional[RatePolicy] = None,
        rate_delay: Optional[int] = None,
        schedule: Optional[Schedule] = None,
    ) -> None:
        self._widget: object = None
        # Bumped on each render, so emits from an old widget's handlers are
        # dropped even if its detach failed to remove them.
        self._generation = 0
        self._slots: Dict[str, Slot] = {}
        self.values: Dict[str, reactive.Value[Box]] = {}
        for spec in specs:
            slot = Slot(spec)
            policy = spec.rate_policy
            if policy is not None:
                slot.limiter = RateLimiter(
                    lambda slot=slot: self._publish(slot),
                    policy=rate_policy or policy,
                    delay_ms=spec.rate_delay if rate_delay is None else rate_delay,
                    schedule=schedule,
                )
            self._slots[spec.name] = slot
            self.values[spec.name] = reactive.Value(Box(None))

    def names(self) -> Tuple[str, ...]:
        return tuple(self._slots)

    def on_render(self, widget: object) -> None:
        self._generation += 1
        self._widget = widget
        for slot in self._slots.values():
            slot.release()
            if slot.spec.kind == "event":
                self._reset(slot)
            if slot.spec.eager or slot.activated:
                self._attach(slot)

    def read(self, name: str, *, raw: bool = False) -> object:
        slot = self._slots[name]
        if self._widget is not None and slot.detach is None:
            # Attach before taking the dependency, so a value the attach
            # emits right away doesn't invalidate this reader.
            self._attach(slot)
        value = self.values[name]
        if has_current_context():
            box = value.get()
        else:
            with reactive.isolate():
                box = value.get()
        if self._widget is None or slot.spec.not_ready(box.raw):
            req(False)
        if box.raw is None or raw:
            return box.raw
        if slot.memo_box is not box:
            slot.memo = slot.spec.payload(box.raw)
            slot.memo_box = box
        return slot.memo

    def close(self) -> None:
        self._generation += 1
        self._widget = None
        for slot in self._slots.values():
            slot.release()

    def _attach(self, slot: Slot) -> None:
        generation = self._generation

        def emit(raw: object) -> None:
            if generation != self._generation:
                return
            if slot.spec.priority == "input" and payloads_equal(raw, slot.latest):
                return
            slot.latest = raw
            # A value reported while attaching is the widget's current state,
            # not part of a stream, so it shouldn't wait out a debounce.
            if slot.limiter is None or attaching:
                self._publish(slot)
            else:
                slot.limiter.call()

        slot.activated = True
        attaching = True
        try:
            slot.detach = slot.spec.attach(self._widget, emit)
        finally:
            attaching = False

    def _publish(self, slot: Slot) -> None:
        self.values[slot.spec.name].set(Box(slot.latest))
        for name in slot.spec.clears:
            self._reset(self._slots[name])

    def _reset(self, slot: Slot) -> None:
        slot.latest = None
        value = self.values[slot.spec.name]
        with reactive.isolate():
            current = value.get()
        if current.raw is not None:
            value.set(Box(None))


class Slot:
    """Per-accessor bookkeeping for `Accessors`."""

    def __init__(self, spec: AccessorSpec) -> None:
        self.spec = spec
        self.limiter: Optional[RateLimiter] = None
        self.detach: Optional[Callable[[], None]] = None
        # Read at least once, so it re-attaches on every later render.
        self.activated = False
        # The last raw value emitted (published, or waiting on the limiter).
        self.latest: object = None
        self.memo_box: Optional[Box] = None
        self.memo: object = None

    def release(self) -> None:
        if self.detach is not None:
            detach, self.detach = self.detach, None
            detach()
        if self.limiter is not None:
            self.limiter.cancel()


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


def has_current_context() -> bool:
    try:
        get_current_context()
        return True
    except RuntimeError:
        return False
