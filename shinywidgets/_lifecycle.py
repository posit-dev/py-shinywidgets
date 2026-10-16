from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, cast
from uuid import uuid4
from weakref import WeakKeyDictionary

from ipywidgets import Widget
from shiny import Session

from ._comm import OrphanedShinyComm, ShinyCommManager

__all__ = (
    "ClosedWidget",
    "Lifetime",
    "LifecycleSnapshot",
    "SessionLifecycle",
    "WidgetRecord",
    "get_lifecycle",
)


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
        self._closed_widgets: WeakKeyDictionary[Widget, ClosedWidget] = (
            WeakKeyDictionary()
        )

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
