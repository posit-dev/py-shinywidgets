from __future__ import annotations

import asyncio
import weakref
from dataclasses import dataclass
from typing import Any, Callable, Dict, Literal, Optional, Sequence, Tuple

from shiny import Session, reactive, req
from shiny.reactive._core import (
    get_current_context,  # pyright: ignore[reportPrivateImportUsage]
)
from shiny.session import get_current_session

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
        Default rate limit (`rate_delay` in seconds), overridable by the
        renderer's kwargs.
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
    rate_delay: float = 0.25
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


def register_rate_policy(
    widget: object, policy: Optional[RatePolicy], delay: Optional[float]
) -> None:
    """
    Rate-limit `reactive_read()` on `widget`, as the renderer that rendered it
    asked (`policy=None` removes the limit).
    """
    key = id(widget)
    delay = 0.25 if delay is None else delay
    current = RATE_POLICIES.get(key)
    if policy is None:
        RATE_POLICIES.pop(key, None)
    elif current is None or (current.policy, current.delay) != (policy, delay):
        if current is None:
            # Keyed by id, since widgets may be unhashable (plotly's
            # FigureWidget defines __eq__ without __hash__)
            weakref.finalize(widget, RATE_POLICIES.pop, key, None)
        RATE_POLICIES[key] = WidgetRate(policy, delay)


def rate_policy_for(widget: object) -> Optional[WidgetRate]:
    return RATE_POLICIES.get(id(widget))


class WidgetRate:
    """
    One widget's rate limit for `reactive_read()`, shared by every reader so
    that a throttle window outlives the reactive re-runs it causes.

    A shared widget's readers span sessions, so its timers belong to none of
    them (a session's queued work is dropped when it ends, which would leave a
    window open for good); each delayed invalidation goes through its reader's
    own session instead.
    """

    def __init__(self, policy: RatePolicy, delay: float) -> None:
        self.policy: RatePolicy = policy
        self.delay = delay
        self._pending: Dict[int, Tuple[Callable[[], None], Optional[Session]]] = {}
        self._calling = False
        self._limiter = RateLimiter(
            self._fire, policy=policy, delay=delay, schedule=timer_schedule
        )

    def invalidate(
        self, key: int, fn: Callable[[], None], session: Optional[Session]
    ) -> None:
        """Run `fn` (invalidating a reader in `session`) as the rate allows."""
        self._pending[key] = (fn, session)
        self._calling = True
        try:
            self._limiter.call()
        finally:
            self._calling = False

    def discard(self, key: int) -> None:
        self._pending.pop(key, None)

    def _fire(self) -> None:
        pending = list(self._pending.values())
        self._pending.clear()
        for fn, session in pending:
            if self._calling or session is None or session.is_stub_session():
                fn()  # the leading edge, inside the cycle that changed the trait
            else:
                session.root_scope().run_once_when_idle(fn)


RATE_POLICIES: Dict[int, WidgetRate] = {}


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
        rate_delay: Optional[float] = None,
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
                    delay=spec.rate_delay if rate_delay is None else rate_delay,
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
            else:
                # Drop a value the limiter was holding: the new widget reports
                # its own state, which must not be deduped against it.
                slot.latest = self._published(slot)
            if widget is not None and (slot.spec.eager or slot.activated):
                try:
                    self._attach(slot)
                except Exception:
                    # e.g. a layout this accessor doesn't support: render it
                    # anyway, and let the next read retry the attach and raise
                    slot.activated = False

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

        attaching = True
        try:
            slot.detach = slot.spec.attach(self._widget, emit)
        finally:
            attaching = False
        # Only now: an attach that raised (e.g. an unsupported layout) must
        # not be retried, and raise, inside a later render.
        slot.activated = True

    def _publish(self, slot: Slot) -> None:
        self.values[slot.spec.name].set(Box(slot.latest))

    def _reset(self, slot: Slot) -> None:
        slot.latest = None
        if self._published(slot) is not None:
            self.values[slot.spec.name].set(Box(None))

    def _published(self, slot: Slot) -> object:
        with reactive.isolate():
            return self.values[slot.spec.name].get().raw


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
        delay: float,
        schedule: Optional[Schedule] = None,
    ) -> None:
        self._fn = fn
        self._policy = policy if delay > 0 else None
        self._delay = delay
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


def timer_schedule(delay: float, fn: Callable[[], None]) -> Callable[[], None]:
    handle = asyncio.get_running_loop().call_later(delay, fn)
    return handle.cancel


def loop_schedule(delay: float, fn: Callable[[], None]) -> Callable[[], None]:
    cancelled = False

    def run() -> None:
        if not cancelled:
            fn()

    session = get_current_session()
    if session is not None and not session.is_stub_session():
        # A timer fires outside the session's cycle, where py-shiny only lets
        # reactive state change at the start of the next one.
        root = session.root_scope()
        handle = asyncio.get_running_loop().call_later(
            delay, lambda: root.run_once_when_idle(run)
        )
    else:
        handle = asyncio.get_running_loop().call_later(delay, run)

    def cancel() -> None:
        nonlocal cancelled
        cancelled = True
        handle.cancel()

    return cancel


def _numpy() -> Any:
    # numpy is optional, so import it lazily (and only once); returns the
    # module, or None when it isn't installed
    global _NUMPY
    if _NUMPY is _UNTRIED:
        try:
            import numpy as np
        except ImportError:
            _NUMPY = None
        else:
            _NUMPY = np
    return _NUMPY


_UNTRIED = object()
_NUMPY: Any = _UNTRIED


def payloads_equal(a: object, b: object) -> bool:
    if a is b:
        return True
    # Arrays compare elementwise, and bool() of the result warns (numpy < 2,
    # where equal empties would then republish) or raises, so compare them
    # with np.array_equal before the generic equality below.
    np = _numpy()
    if np is not None and isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        return bool(np.array_equal(a, b))
    try:
        return bool(a == b)
    except (ValueError, TypeError):
        # Other array-likes (pandas) compare elementwise, and their truth
        # value is ambiguous.
        return False


def has_current_context() -> bool:
    try:
        get_current_context()
        return True
    except RuntimeError:
        return False
