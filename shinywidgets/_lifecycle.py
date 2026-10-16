from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Generic, Literal, TypeVar, cast
from uuid import uuid4
from weakref import WeakKeyDictionary, ref

from ipywidgets import Widget
from shiny import Session
from shiny.session import get_current_session

from ._comm import OrphanedShinyComm, ShinyCommManager

__all__ = (
    "ClosedWidget",
    "Lifetime",
    "LifecycleSnapshot",
    "SessionLifecycle",
    "WidgetRecord",
    "get_lifecycle",
    "session_lifetime",
    "use_lifetime",
)


@contextmanager
def session_lifetime() -> Iterator[None]:
    """
    Retain widgets constructed inside this block for the current Shiny session.

    Widgets created while rendering an output are temporary: they are closed
    when that render is retired. Constructing a widget inside
    `session_lifetime()` gives it the session's lifetime instead, so it
    survives re-renders and can be displayed again later (for example, a widget
    cached per dataset).

    Exiting the block restores the previous construction policy; it does not
    close widgets created inside the block. Referencing, assigning, or
    returning an existing widget inside the block does not transfer that
    widget's lifetime. Retained widgets are closed when the session ends.

    Raises
    ------
    RuntimeError
        If there is no active Shiny session.
    """
    session = get_current_session()
    if session is None:
        raise RuntimeError("session_lifetime() requires an active Shiny session")
    # On the Express discovery pass, there is no real session yet; the same app
    # source runs again on the real session pass.
    if session.is_stub_session():
        yield
        return
    lifecycle = get_lifecycle(session.root_scope())
    with use_lifetime(lifecycle.session_lifetime):
        yield


V = TypeVar("V")


class WidgetWeakMap(Generic[V]):
    """
    An identity-keyed map from widgets to values that never retains its keys.

    Unlike WeakKeyDictionary, this works with widgets that are unhashable
    (e.g., plotly's FigureWidget defines __eq__ without __hash__).
    """

    def __init__(self) -> None:
        self._data: dict[int, tuple[ref[Widget], V]] = {}

    def __setitem__(self, widget: Widget, value: V) -> None:
        key = id(widget)
        data = self._data

        def remove(_: ref[Widget], key: int = key) -> None:
            data.pop(key, None)

        self._data[key] = (ref(widget, remove), value)

    def get(self, widget: Widget) -> V | None:
        entry = self._data.get(id(widget))
        if entry is None:
            return None
        widget_ref, value = entry
        if widget_ref() is not widget:
            return None
        return value


@dataclass(eq=False)
class Lifetime:
    session_id: str
    kind: Literal["session", "render"]
    generation_id: str
    accepting: bool = True
    roots: set[str] = field(default_factory=set)


@dataclass
class WidgetRecord:
    widget: Widget
    model_id: str
    lifetime: Lifetime
    state: Literal["pending", "opening", "open", "closed"] = "pending"
    cancel_initializer: Callable[[], None] | None = None


@dataclass(frozen=True)
class ClosedWidget:
    model_id: str
    session_id: str
    reason: str


@dataclass(frozen=True)
class LifecycleSnapshot:
    records: int
    comms: int
    pending_initializers: int
    render_lifetimes: int
    display_leases: int = 0


def get_lifecycle(session: Session) -> SessionLifecycle:
    """
    Get (or create) the widget lifecycle manager for a Shiny session.

    The session is normalized to its root scope so module-scoped sessions share
    the root session's manager. The manager is removed when the session ends.
    """
    root = session.root_scope()
    lifecycle = _lifecycles.get(root)
    if lifecycle is None:
        lifecycle = SessionLifecycle(root)
        _lifecycles[root] = lifecycle

        def cleanup() -> None:
            lifecycle.close_session()
            # The manager retains its session (a value -> key strong reference),
            # so remove the entry explicitly; weak keys alone don't break that cycle.
            _lifecycles.pop(root, None)

        root.on_ended(cleanup)
    return lifecycle


class SessionLifecycle:
    """
    Owns the widget records, comm manager, and lifetimes of one Shiny session.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.session_lifetime = Lifetime(
            session_id=session.id, kind="session", generation_id=session.id
        )
        self.records: dict[str, WidgetRecord] = {}
        self.comm_manager = ShinyCommManager()
        self.render_lifetimes: set[Lifetime] = set()
        self.wired: bool = False
        self._closed_widgets: WidgetWeakMap[ClosedWidget] = WidgetWeakMap()

    def register(self, widget: Widget, lifetime: Lifetime) -> WidgetRecord:
        if lifetime.session_id != self.session.id:
            raise RuntimeError(
                "Cannot construct a widget under a lifetime that belongs to a "
                "different Shiny session. Widgets cannot be shared across sessions."
            )
        if not lifetime.accepting:
            raise RuntimeError("Cannot construct widgets in a retired lifetime")
        if getattr(widget, "_model_id", None) is None:
            widget._model_id = uuid4().hex
        model_id = cast(str, widget._model_id)
        if model_id in self.records:
            raise RuntimeError(
                f"A widget with model_id '{model_id}' is already registered in "
                "this session."
            )
        record = WidgetRecord(widget=widget, model_id=model_id, lifetime=lifetime)
        self.records[model_id] = record
        lifetime.roots.add(model_id)
        _widget_owners[widget] = ref(self)
        return record

    def set_initializer(self, record: WidgetRecord, cancel: Callable[[], None]) -> None:
        if record.state == "closed":
            cancel()
            return
        record.cancel_initializer = cancel

    def close_record(self, model_id: str, reason: str = "closed") -> None:
        record = self.records.pop(model_id, None)
        if record is None:
            return
        record.state = "closed"
        record.lifetime.roots.discard(model_id)
        cancel = record.cancel_initializer
        record.cancel_initializer = None
        if cancel is not None:
            cancel()
        widget = record.widget
        # The tombstone holds only inert strings so it never retains the widget,
        # its record, or this manager.
        self._closed_widgets[widget] = ClosedWidget(
            model_id=model_id, session_id=self.session.id, reason=reason
        )
        # Mark the record closed (above) before closing the widget: closing the
        # widget closes its comm, which notifies back into close_record(); the
        # record being gone already makes that recursion harmless.
        if widget.comm is not None:
            widget.close()
        # Preserve the closed widget's stable ID (some packages, e.g. ipyleaflet,
        # use the IDs of children when removing them from parent collections).
        # The orphaned comm is inert metadata; it does not make the widget live.
        widget.comm = OrphanedShinyComm(model_id)
        # Assigning a comm re-registers the widget in the ipywidgets instance
        # map; remove that entry again (by identity) so the widget can be
        # garbage collected.
        instances = cast(dict[str, Widget], Widget.widgets)
        if instances.get(model_id) is widget:
            del instances[model_id]

    def check_displayable(self, widget: Widget) -> None:
        """
        Raise if a widget returned from a render function can't be displayed:
        either it belongs to a different session, or it was already closed
        (e.g., its render lifetime ended). An inert model ID on a closed
        widget is not evidence that the widget is still live.
        """
        owner_ref = _widget_owners.get(widget)
        owner = owner_ref() if owner_ref is not None else None
        if owner is not None and owner is not self:
            raise RuntimeError(
                "This widget belongs to a different Shiny session. Widgets "
                "can't be shared across sessions; construct one widget per "
                "session instead."
            )
        if owner is None:
            return
        model_id = cast(str | None, getattr(widget, "_model_id", None))
        if model_id is not None and model_id in self.records:
            return
        closed = self._closed_widgets.get(widget)
        if closed is not None and closed.reason == "render-retired":
            raise RuntimeError(
                "This widget's render lifetime has ended. Create reusable "
                "widgets inside session_lifetime()."
            )
        raise RuntimeError(
            "This widget has been closed and can't be rendered again. Create "
            "reusable widgets inside session_lifetime()."
        )

    def new_render_lifetime(self) -> Lifetime:
        if not self.session_lifetime.accepting:
            raise RuntimeError("Cannot render widgets: the Shiny session has ended")
        lifetime = Lifetime(
            session_id=self.session.id, kind="render", generation_id=uuid4().hex
        )
        self.render_lifetimes.add(lifetime)
        return lifetime

    def retire_render(self, lifetime: Lifetime) -> None:
        if lifetime.kind != "render":
            raise ValueError("retire_render() expects a render lifetime")
        if lifetime not in self.render_lifetimes:
            return
        # Stop admission of new temporary work before closing this phase's
        # temporary records.
        lifetime.accepting = False
        self.render_lifetimes.discard(lifetime)
        for model_id in list(lifetime.roots):
            self.close_record(model_id, reason="render-retired")

    def close_session(self) -> None:
        self.session_lifetime.accepting = False
        for lifetime in self.render_lifetimes:
            lifetime.accepting = False
        self.render_lifetimes.clear()
        # Disable new sends before closing records so close() doesn't attempt to
        # publish on a terminated connection.
        self.comm_manager.active = False
        for model_id in list(self.records):
            self.close_record(model_id, reason="session-ended")

    def snapshot(self) -> LifecycleSnapshot:
        return LifecycleSnapshot(
            records=len(self.records),
            comms=len(self.comm_manager.comms),
            pending_initializers=sum(
                1 for record in self.records.values() if record.state == "pending"
            ),
            render_lifetimes=len(self.render_lifetimes),
        )


_lifecycles: WeakKeyDictionary[Session, SessionLifecycle] = WeakKeyDictionary()

# The explicitly selected construction lifetime for the current context
# (e.g., inside a `session_lifetime()` block). Overrides the render/session
# defaults until the block exits.
selected_lifetime: ContextVar[Lifetime | None] = ContextVar(
    "shinywidgets_lifetime", default=None
)

# Weak widget -> owning manager index. Values are weak references so neither
# the widget nor its manager is retained by this index.
_widget_owners: WidgetWeakMap[ref[SessionLifecycle]] = WidgetWeakMap()


@contextmanager
def use_lifetime(lifetime: Lifetime) -> Iterator[None]:
    if not lifetime.accepting:
        raise RuntimeError("Cannot construct widgets in a retired lifetime")
    token = selected_lifetime.set(lifetime)
    try:
        yield
    finally:
        selected_lifetime.reset(token)
