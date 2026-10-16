from __future__ import annotations

import warnings
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
from ._widget_dependencies import dependencies, unreachable

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
    disposers: list[Callable[[], None]] = field(default_factory=list)


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


@dataclass(frozen=True)
class EpochIdentity:
    """
    The session model namespace (stable for the session's life) and transport
    epoch (fresh per connection) that qualify this session's widget protocol.
    """

    session_id: str
    model_namespace: str
    epoch_id: str


@dataclass
class DisplayLease:
    lease_id: str
    output_id: str
    generation_id: str
    root_id: str
    offer_id: str
    mount_id: str | None = None
    claim_seq: int | None = None


@dataclass
class Publication:
    """
    The current published widget value for an output: its offer, root, render
    generation, and initial provisional display lease.
    """

    output_id: str
    offer_id: str
    generation_id: str
    root_id: str
    provisional_lease_id: str


@dataclass
class OutputClaimState:
    """
    The current claim sequence/outcome terminal for one output. Storing only
    the latest terminal (rather than every mount's history) keeps claims
    idempotent and bounded.
    """

    latest_seq: int = 0
    latest_mount_id: str = ""
    latest_outcome: dict[str, object] = field(default_factory=dict)
    cancelled_seqs: set[int] = field(default_factory=set)


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
        self.epoch = EpochIdentity(
            session_id=session.id,
            model_namespace=uuid4().hex[:12],
            epoch_id=uuid4().hex[:12],
        )
        self.records: dict[str, WidgetRecord] = {}
        self.comm_manager = ShinyCommManager()
        self.render_lifetimes: set[Lifetime] = set()
        self.publications: dict[str, Publication] = {}
        self.display_leases: dict[str, DisplayLease] = {}
        self._claim_states: dict[str, OutputClaimState] = {}
        self.wired: bool = False
        self._closed_widgets: WidgetWeakMap[ClosedWidget] = WidgetWeakMap()
        self._revision: int = 0
        self._collecting: bool = False
        self._collect_pending: bool = False
        self._preparing: int = 0
        self._incomplete_warned: bool = False

    def register(self, widget: Widget, lifetime: Lifetime) -> WidgetRecord:
        if lifetime.session_id != self.session.id:
            raise RuntimeError(
                "Cannot construct a widget under a lifetime that belongs to a "
                "different Shiny session. Widgets cannot be shared across sessions."
            )
        if not lifetime.accepting:
            raise RuntimeError("Cannot construct widgets in a retired lifetime")
        local_id = getattr(widget, "_model_id", None)
        if local_id is None:
            local_id = uuid4().hex
        model_id = self.qualify_model_id(local_id)
        widget._model_id = model_id
        if model_id in self.records:
            raise RuntimeError(
                f"A widget with model_id '{model_id}' is already registered in "
                "this session."
            )
        record = WidgetRecord(widget=widget, model_id=model_id, lifetime=lifetime)
        self.records[model_id] = record
        self._revision += 1
        lifetime.roots.add(model_id)
        _widget_owners[widget] = ref(self)
        return record

    def qualify_model_id(self, local_id: str) -> str:
        """
        Qualify a model ID with this session's namespace at construction,
        before comm assignment. Full IDs in this session's namespace are
        accepted opaquely; another namespace is rejected (never relabel a
        live model).
        """
        prefix = f"sw-{self.epoch.model_namespace}-"
        if local_id.startswith("sw-"):
            if local_id.startswith(prefix):
                return local_id
            raise RuntimeError(
                f"Model ID '{local_id}' belongs to a different session "
                "namespace. Widgets can't share model IDs across sessions."
            )
        return prefix + local_id

    def publish(self, output_id: str, generation_id: str, root_id: str) -> Publication:
        """
        Publish the current widget value for an output. Publishing a newer
        value invalidates the previous offer and releases its unclaimed
        provisional lease (an already-claimed lease is kept until its
        presentation release).
        """
        self.retract(output_id)
        offer_id = uuid4().hex
        lease_id = uuid4().hex
        self.display_leases[lease_id] = DisplayLease(
            lease_id=lease_id,
            output_id=output_id,
            generation_id=generation_id,
            root_id=root_id,
            offer_id=offer_id,
        )
        publication = Publication(
            output_id=output_id,
            offer_id=offer_id,
            generation_id=generation_id,
            root_id=root_id,
            provisional_lease_id=lease_id,
        )
        self.publications[output_id] = publication
        return publication

    def retract(self, output_id: str) -> None:
        """
        Invalidate the output's current offer (null/error replacement).
        Releases the unclaimed provisional lease; claimed leases stay alive
        until their presentation release.
        """
        previous = self.publications.pop(output_id, None)
        if previous is None:
            return
        lease = self.display_leases.get(previous.provisional_lease_id)
        if lease is not None and lease.mount_id is None:
            del self.display_leases[previous.provisional_lease_id]

    def acquire_display(
        self, output_id: str, generation_id: str, root_id: str, offer_id: str
    ) -> DisplayLease:
        lease_id = uuid4().hex
        lease = DisplayLease(
            lease_id=lease_id,
            output_id=output_id,
            generation_id=generation_id,
            root_id=root_id,
            offer_id=offer_id,
        )
        self.display_leases[lease_id] = lease
        return lease

    def release_display(self, lease_id: str) -> None:
        self.display_leases.pop(lease_id, None)
        # Releasing a display lease can make its root collectible.
        self.collect()

    def handle_display_events(self, packet: object) -> dict[str, object]:
        """
        Validate and process a display-events packet (claims, releases, and
        claim cancellations) atomically for this session, and produce the
        per-event results to return to the browser.
        """
        events = validate_display_events(self.epoch, packet)
        results: list[dict[str, object]] = []
        for event in events:
            action = event["action"]
            if action == "claim":
                results.append(self._process_claim(event))
            elif action == "release":
                results.append(self._process_release(event))
            elif action == "cancel-claim":
                results.append(self._process_cancel(event))
        return {
            "sw": 1,
            "version": 1,
            "session_id": self.epoch.session_id,
            "model_namespace": self.epoch.model_namespace,
            "epoch_id": self.epoch.epoch_id,
            "results": results,
        }

    def _process_claim(self, event: dict[str, object]) -> dict[str, object]:
        output_id = cast(str, event["output_id"])
        mount_id = cast(str, event["mount_id"])
        seq = cast(int, event["claim_seq"])
        state = self._claim_states.setdefault(output_id, OutputClaimState())
        result = {
            "event_id": event["event_id"],
            "output_id": output_id,
            "mount_id": mount_id,
            "claim_seq": seq,
        }
        # Idempotent replay: the same mount repeating the current terminal
        # sequence gets the recorded outcome (never acquires twice).
        if (
            seq == state.latest_seq
            and mount_id == state.latest_mount_id
            and state.latest_outcome
        ):
            return {**result, "outcome": dict(state.latest_outcome)}
        if seq < state.latest_seq:
            return {**result, "outcome": {"refused": "superseded"}}
        publication = self.publications.get(output_id)
        outcome: dict[str, object]
        if publication is None or publication.offer_id != event["offer_id"]:
            outcome = {"refused": "stale-offer"}
        elif publication.root_id != event["root_id"]:
            outcome = {"refused": "stale-offer"}
        elif publication.root_id not in self.records:
            # Never reopen or resurrect a collected widget.
            outcome = {"refused": "root-closed"}
        else:
            state.latest_seq = seq
            state.latest_mount_id = mount_id
            lease = self.display_leases.get(publication.provisional_lease_id)
            if lease is not None and lease.mount_id is None:
                lease.mount_id = mount_id
                lease.claim_seq = seq
                outcome = {"claimed": lease.lease_id}
            else:
                # The provisional lease was already consumed (e.g., a cached
                # value replay on a new mount); renew with a fresh lease.
                new_lease = self.acquire_display(
                    publication.output_id,
                    publication.generation_id,
                    publication.root_id,
                    publication.offer_id,
                )
                new_lease.mount_id = mount_id
                new_lease.claim_seq = seq
                outcome = {"claimed": new_lease.lease_id}
            state.latest_outcome = outcome
            return {**result, "outcome": outcome}
        return {**result, "outcome": outcome}

    def _process_release(self, event: dict[str, object]) -> dict[str, object]:
        lease_id = cast(str, event["lease_id"])
        result = {
            "event_id": event["event_id"],
            "output_id": event["output_id"],
            "mount_id": event["mount_id"],
        }
        lease = self.display_leases.get(lease_id)
        if lease is None:
            # An unknown inactive release is an acknowledged no-op (leases are
            # never re-minted, so it can't refer to a future lease).
            return {**result, "outcome": {"acked": True}}
        if lease.output_id != event["output_id"] or lease.mount_id != event["mount_id"]:
            raise RuntimeError(
                "Display release doesn't match the lease's recorded "
                "output/mount association"
            )
        self.release_display(lease_id)
        return {**result, "outcome": {"acked": True}}

    def _process_cancel(self, event: dict[str, object]) -> dict[str, object]:
        output_id = cast(str, event["output_id"])
        mount_id = cast(str, event["mount_id"])
        seq = cast(int, event["claim_seq"])
        state = self._claim_states.setdefault(output_id, OutputClaimState())
        if seq >= state.latest_seq:
            # Record a terminal cancellation so a late claim for this sequence
            # is refused.
            state.latest_seq = seq
            state.latest_mount_id = mount_id
            state.latest_outcome = {"refused": "cancelled"}
        return {
            "event_id": event["event_id"],
            "output_id": output_id,
            "mount_id": mount_id,
            "claim_seq": seq,
            "outcome": {"acked": True},
        }

    def set_initializer(self, record: WidgetRecord, cancel: Callable[[], None]) -> None:
        if record.state == "closed":
            cancel()
            return
        record.cancel_initializer = cancel

    def close_record(self, model_id: str, reason: str = "closed") -> None:
        record = self.records.pop(model_id, None)
        if record is None:
            return
        self._revision += 1
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

    def add_disposer(self, lifetime: Lifetime, disposer: Callable[[], None]) -> None:
        """
        Register cleanup for a non-model resource (e.g., a Python `link()`'s
        `unlink`) owned by a lifetime. Disposers run once, after the
        lifetime's admission closes. Registering with an already-retired
        lifetime invokes the disposer immediately.
        """
        if lifetime.session_id != self.session.id:
            raise RuntimeError(
                "Cannot register a disposer for another session's lifetime"
            )
        if not lifetime.accepting:
            disposer()
            return
        lifetime.disposers.append(disposer)

    def retire_render(self, lifetime: Lifetime) -> None:
        if lifetime.kind != "render":
            raise ValueError("retire_render() expects a render lifetime")
        if lifetime not in self.render_lifetimes:
            return
        # Stop admission of new temporary work, then release this lifetime's
        # roots: collection closes the records that can't be reached from the
        # remaining live roots (a live shared widget may still reference them).
        lifetime.accepting = False
        self.render_lifetimes.discard(lifetime)
        self.collect()
        self._run_disposers(lifetime)

    def _run_disposers(self, lifetime: Lifetime) -> None:
        disposers = lifetime.disposers
        lifetime.disposers = []
        for dispose in disposers:
            try:
                dispose()
            except Exception as e:
                warnings.warn(
                    f"Error disposing a widget resource: {e}",
                    RuntimeWarning,
                    stacklevel=2,
                )

    def collect(self) -> None:
        """
        Close records that can't be reached from live lifetime roots.

        Edges are refreshed from materialized trait values at collection time,
        so in-place container mutations (which need not notify) are accounted
        for. Reentrant requests are coalesced rather than recursive.
        """
        if self._collecting or self._preparing > 0:
            self._collect_pending = True
            return
        self._collecting = True
        try:
            while True:
                self._collect_pending = False
                self._collect_once()
                if not self._collect_pending:
                    break
        finally:
            self._collecting = False

    def begin_preparation(self) -> None:
        """Mark a batch of deferred state preparation (defaults/serializers)."""
        self._preparing += 1

    def end_preparation(self) -> None:
        self._preparing -= 1
        if self._preparing == 0 and self._collect_pending:
            self.collect()

    def _collect_once(self) -> None:
        if not self.session_lifetime.accepting:
            # Session close is unconditional and doesn't consult the graph.
            return
        revision = self._revision
        roots = set(self.session_lifetime.roots)
        for lifetime in self.render_lifetimes:
            roots |= lifetime.roots
        # Displayed roots stay alive while their display lease is active; the
        # browser releases the lease after removing the presentation.
        for lease in self.display_leases.values():
            roots.add(lease.root_id)
        snapshots = {
            model_id: dependencies(record.widget)
            for model_id, record in self.records.items()
        }
        if revision != self._revision:
            # Registration changed while preparing the snapshot; rebuild it
            # before closing anything.
            self._collect_pending = True
            return
        graph: dict[str, frozenset[str]] = {}
        for model_id, snapshot in snapshots.items():
            edges: set[str] = set()
            for dep in snapshot.widgets:
                # Only live records owned by this manager can keep a record
                # alive; a closed or foreign-session dependency's comm ID is
                # not evidence of ownership.
                owner_ref = _widget_owners.get(dep)
                owner = owner_ref() if owner_ref is not None else None
                if owner is not self:
                    continue
                dep_id = cast(str | None, getattr(dep, "_model_id", None))
                if dep_id is not None and dep_id in self.records:
                    edges.add(dep_id)
            graph[model_id] = frozenset(edges)
        candidates = unreachable(roots & set(graph), graph)
        reachable = set(graph) - candidates
        if any(not snapshots[model_id].complete for model_id in reachable):
            # A live record hides dependencies behind a custom serializer that
            # has no adapter. Retain everything (rather than risk closing a
            # hidden dependency of a live widget) and emit one diagnostic while
            # the incompleteness persists.
            if not self._incomplete_warned:
                self._incomplete_warned = True
                warnings.warn(
                    "shinywidgets can't determine the full widget dependency "
                    "graph because a live widget uses a custom trait serializer. "
                    "Temporary widgets won't be collected while it is live.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            return
        self._incomplete_warned = False
        for model_id in candidates:
            self.close_record(model_id, reason="render-retired")

    def close_session(self) -> None:
        self.session_lifetime.accepting = False
        for lifetime in self.render_lifetimes:
            lifetime.accepting = False
            self._run_disposers(lifetime)
        self.render_lifetimes.clear()
        self._run_disposers(self.session_lifetime)
        self.publications.clear()
        self.display_leases.clear()
        self._claim_states.clear()
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
            display_leases=len(self.display_leases),
        )


def validate_display_events(
    epoch: EpochIdentity, packet: object
) -> list[dict[str, object]]:
    """
    Strictly validate a display-events packet against the session's epoch and
    return its events. Invalid packets are never acknowledged as successful.
    """
    if not isinstance(packet, dict) or packet.get("sw") != 1:
        raise RuntimeError(
            "Received a legacy shinywidgets display packet (missing the "
            "versioned envelope)"
        )
    if packet.get("version") != 1:
        raise RuntimeError("Unsupported shinywidgets display packet version")
    if (
        packet.get("session_id") != epoch.session_id
        or packet.get("model_namespace") != epoch.model_namespace
        or packet.get("epoch_id") != epoch.epoch_id
    ):
        raise RuntimeError(
            "Received shinywidgets display events for a different session/epoch"
        )
    events = packet.get("events")
    if not isinstance(events, list):
        raise RuntimeError("Malformed shinywidgets display packet (no events)")
    validated: list[dict[str, object]] = []
    required: dict[str, set[str]] = {
        "claim": {
            "event_id",
            "output_id",
            "offer_id",
            "candidate_lease_id",
            "generation_id",
            "root_id",
            "mount_id",
            "claim_seq",
        },
        "release": {
            "event_id",
            "output_id",
            "lease_id",
            "mount_id",
            "presentation_removed",
            "reason",
            "cleanup",
        },
        "cancel-claim": {"event_id", "output_id", "mount_id", "claim_seq"},
    }
    for event in events:
        if not isinstance(event, dict):
            raise RuntimeError("Malformed shinywidgets display event")
        action = event.get("action")
        fields = required.get(cast(str, action))
        if fields is None:
            raise RuntimeError(f"Unknown shinywidgets display action: {action!r}")
        missing = fields - set(event)
        if missing:
            raise RuntimeError(
                f"Malformed shinywidgets display event (missing {sorted(missing)})"
            )
        if "claim_seq" in fields and not isinstance(event["claim_seq"], int):
            raise RuntimeError("claim_seq must be an integer")
        validated.append(event)
    return validated


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
