from __future__ import annotations

import asyncio

import pytest
from ipywidgets import HTML, Box, IntSlider, Widget, jslink, widget_serialization
from shiny import Session, reactive
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets import session_lifetime
from shinywidgets._lifecycle import get_lifecycle
from shinywidgets._render_widget_base import WidgetRenderContext
from shinywidgets._widget_dependencies import (
    DependencyAdapter,
    dependencies,
    references,
    register_serializer_adapter,
    unreachable,
)
from traitlets import Any, default


class ReferenceWidget(Widget):
    ref = Any().tag(sync=True, **widget_serialization)


class LazyDefaultWidget(Widget):
    lazy = Any().tag(sync=True, **widget_serialization)

    def __init__(self) -> None:
        self.default_calls = 0
        super().__init__()

    @default("lazy")
    def default_lazy(self) -> HTML:
        self.default_calls += 1
        return HTML(value="lazy")


class HiddenReference:
    """A trait value that refers to a widget only through a plain attribute,
    which supported container serialization never inspects."""

    def __init__(self, target: Widget) -> None:
        self.target = target


def hidden_serializer(value: object, widget: object) -> object:
    """A custom serializer that emits a widget's ID although the raw trait
    value contains no Widget reachable by supported serialization."""
    if not isinstance(value, HiddenReference):
        return None
    return f"IPY_MODEL_{value.target.model_id}"


class HiddenTargetWidget(Widget):
    hidden = Any().tag(sync=True, to_json=hidden_serializer)


def unadapted_hidden_serializer(value: object, widget: object) -> object:
    return hidden_serializer(value, widget)


class UnadaptedHiddenWidget(Widget):
    hidden = Any().tag(sync=True, to_json=unadapted_hidden_serializer)


def test_references_are_objects_not_strings(widget_session: Session) -> None:
    with session_context(widget_session):
        child = HTML(value="child")
        value = {"items": [child, (child, f"IPY_MODEL_{child.model_id}")]}
        assert references(value) == frozenset({child})
        assert references(f"IPY_MODEL_{child.model_id}") == frozenset()


def test_references_tolerates_container_cycles(widget_session: Session) -> None:
    with session_context(widget_session):
        child = HTML(value="child")
        value: list[object] = [child]
        value.append(value)
        assert references(value) == frozenset({child})


def test_snapshot_does_not_materialize_lazy_defaults(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        widget = LazyDefaultWidget()
        snapshot = dependencies(widget)
    assert widget.default_calls == 0
    assert snapshot.widgets == frozenset()
    assert snapshot.complete


def test_snapshot_extracts_materialized_children(widget_session: Session) -> None:
    with session_context(widget_session):
        child = HTML(value="child")
        box = Box(children=[child])
        snapshot = dependencies(box)
    assert child in snapshot.widgets
    assert snapshot.complete


def test_unknown_custom_serializer_is_opaque(widget_session: Session) -> None:
    with session_context(widget_session):
        target = HTML(value="hidden")
        widget = HiddenTargetWidget()
        widget.hidden = HiddenReference(target)
        snapshot = dependencies(widget)
    # The raw trait value is a string, not the widget: the dependency is hidden
    # behind the custom serializer, so the trait is reported opaque.
    assert target not in snapshot.widgets
    assert snapshot.opaque_traits == frozenset({"hidden"})
    assert not snapshot.complete


def test_unreachable_collects_a_cycle() -> None:
    graph = {
        "session": frozenset({"shared"}),
        "shared": frozenset(),
        "old-map": frozenset({"old-child"}),
        "old-child": frozenset({"old-map", "shared"}),
    }
    assert unreachable({"session"}, graph) == frozenset({"old-map", "old-child"})


def test_adapter_supplies_hidden_dependencies(widget_session: Session) -> None:
    class HiddenTargetAdapter:
        def dependencies(
            self, widget: Widget, trait_name: str, value: object
        ) -> frozenset[Widget]:
            if isinstance(value, HiddenReference):
                return frozenset({value.target})
            return frozenset()

    _: type[DependencyAdapter] = HiddenTargetAdapter
    register_serializer_adapter(hidden_serializer, HiddenTargetAdapter())

    with session_context(widget_session):
        target = HTML(value="hidden")
        widget = HiddenTargetWidget()
        widget.hidden = HiddenReference(target)
        snapshot = dependencies(widget)
    assert snapshot.widgets == frozenset({target})
    assert snapshot.complete


def test_retirement_collects_widget_cycle(widget_session: Session) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                a = ReferenceWidget()
                b = ReferenceWidget()
                a.ref = b
                b.ref = a
                a_id, b_id = a.model_id, b.model_id
        asyncio.run(reactive.flush())
        assert a_id in lifecycle.records
        context.invalidate()
        asyncio.run(reactive.flush())
    assert a_id not in lifecycle.records
    assert b_id not in lifecycle.records
    assert a_id not in lifecycle.comm_manager.comms


def test_session_root_protects_temporary_dependency(widget_session: Session) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        with session_lifetime():
            shared = ReferenceWidget()
        context = Context()
        with context():
            with WidgetRenderContext():
                temporary = ReferenceWidget()
                temporary_id = temporary.model_id
        # A live session widget references the temporary widget: retiring the
        # render must not close its dependencies.
        shared.ref = temporary
        asyncio.run(reactive.flush())
        context.invalidate()
        asyncio.run(reactive.flush())
    assert temporary_id in lifecycle.records
    assert temporary_id in lifecycle.comm_manager.comms


def test_in_place_dependency_changes_are_collected(widget_session: Session) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        with session_lifetime():
            holder = ReferenceWidget()
            holder.ref = []
        context = Context()
        with context():
            with WidgetRenderContext():
                kept = ReferenceWidget()
                dropped = ReferenceWidget()
                kept_id, dropped_id = kept.model_id, dropped.model_id
        # In-place list mutations don't emit change notifications; the
        # pre-collection refresh must account for them anyway.
        holder.ref.append(kept)
        holder.ref.append(dropped)
        holder.ref.remove(dropped)
        asyncio.run(reactive.flush())
        context.invalidate()
        asyncio.run(reactive.flush())
    assert kept_id in lifecycle.records
    assert dropped_id not in lifecycle.records


def test_jslink_models_are_render_roots_until_retirement(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                s1 = IntSlider()
                s2 = IntSlider()
                link = jslink((s1, "value"), (s2, "value"))
        asyncio.run(reactive.flush())
        ids = {s1.model_id, s2.model_id, link.model_id}
        # The headless link model can't be reached from a displayed parent (it
        # points to the sliders); it is retained as a root of the live render.
        assert ids <= set(lifecycle.records)
        context.invalidate()
        asyncio.run(reactive.flush())
    assert ids.isdisjoint(set(lifecycle.records))


class BorrowedStyleWidget(Widget):
    borrowed: HTML | None
    style_reference = Any().tag(sync=True, **widget_serialization)

    def __init__(self) -> None:
        self.borrowed = None
        super().__init__()

    @default("style_reference")
    def default_style_reference(self) -> object:
        if self.borrowed is None:
            raise RuntimeError("Assign the borrowed popup before initialization")
        return self.borrowed.style


def test_borrowed_late_default_survives_render_retirement(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                borrower = BorrowedStyleWidget()
                borrower_id = borrower.model_id
                with session_lifetime():
                    popup = HTML(value="shared")
                borrower.borrowed = popup
        # The default factory has not run yet, so the popup's style doesn't
        # exist as an object (or a record).
        assert not popup.trait_has_value("style")
        asyncio.run(reactive.flush())
        # Preparation materialized the style under the borrower's (temporary)
        # lifetime...
        assert popup.trait_has_value("style")
        style_id = popup.style.model_id
        assert lifecycle.records[style_id].lifetime.kind == "render"
        context.invalidate()
        lifecycle.collect()
    # ...but the style survives retirement through the live popup's dependency
    # edge, while the temporary borrower is collected.
    assert borrower_id not in lifecycle.records
    assert popup.model_id in lifecycle.records
    assert style_id in lifecycle.records


def test_failed_preparation_closes_record(widget_session: Session) -> None:
    class FailingWidget(Widget):
        def get_state(self, key: object = None, drop_defaults: bool = False) -> object:  # type: ignore[override]
            raise ValueError("serializer failed")

    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        widget = FailingWidget()
        model_id = widget.model_id
        with pytest.warns(RuntimeWarning):
            asyncio.run(reactive.flush())
    assert model_id not in lifecycle.records
    assert model_id not in lifecycle.comm_manager.comms
    # The failed preparation closed the record itself (before Shiny's
    # unhandled-error path closed the session).
    tombstone = lifecycle._closed_widgets.get(widget)
    assert tombstone is not None
    assert tombstone.reason == "initialization-failed"


def test_new_child_of_live_shared_parent_is_retained(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        with session_lifetime():
            parent = Box()
        context = Context()
        with context():
            with WidgetRenderContext():
                child = HTML(value="child")
                child_id = child.model_id
        # Attaching a temporary child to a live shared parent keeps the child
        # alive through the parent's dependency edge after the render retires.
        parent.children = [child]
        asyncio.run(reactive.flush())
        context.invalidate()
        asyncio.run(reactive.flush())
    assert child_id in lifecycle.records
    assert child_id in lifecycle.comm_manager.comms


def test_live_opaque_root_retains_hidden_target(widget_session: Session) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        with session_lifetime():
            source = UnadaptedHiddenWidget()
        context = Context()
        with context():
            with WidgetRenderContext():
                hidden_target = HTML(value="hidden")
                other_temporary = HTML(value="temporary")
                hidden_id = hidden_target.model_id
                other_id = other_temporary.model_id
        source.hidden = HiddenReference(hidden_target)
        asyncio.run(reactive.flush())
        with pytest.warns(RuntimeWarning, match="custom trait serializer"):
            context.invalidate()
            asyncio.run(reactive.flush())
        # While a live root reaches an opaque serializer, collection retains
        # records rather than risk closing a hidden dependency.
        assert hidden_id in lifecycle.records
        assert hidden_id in lifecycle.comm_manager.comms
        assert other_id in lifecycle.records

        # Once the opaque source is gone, a complete snapshot resumes
        # collection.
        source.close()
        lifecycle.collect()
    assert hidden_id not in lifecycle.records
    assert other_id not in lifecycle.records


def test_link_unlink_disposer_runs_at_retirement(widget_session: Session) -> None:
    from ipywidgets import link

    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                s1 = IntSlider(value=1)
                s2 = IntSlider(value=2)
                observer_link = link((s1, "value"), (s2, "value"))
                lifetime = lifecycle.records[s1.model_id].lifetime

        # Widget-model graph collection alone cannot remove the observer link.
        lifecycle.add_disposer(lifetime, observer_link.unlink)
        asyncio.run(reactive.flush())
        context.invalidate()
        asyncio.run(reactive.flush())
        s1.value = 5
    assert s2.value == 1


def test_disposer_failure_reports_and_continues(widget_session: Session) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                widget = HTML(value="x")
                lifetime = lifecycle.records[widget.model_id].lifetime
        ran: list[str] = []

        def failing() -> None:
            raise ValueError("dispose failed")

        lifecycle.add_disposer(lifetime, failing)
        lifecycle.add_disposer(lifetime, lambda: ran.append("second"))
        with pytest.warns(RuntimeWarning, match="dispose failed"):
            context.invalidate()
    assert ran == ["second"]


def test_late_disposer_registration_runs_immediately(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                widget = HTML(value="x")
                lifetime = lifecycle.records[widget.model_id].lifetime
        context.invalidate()
        ran: list[str] = []
        lifecycle.add_disposer(lifetime, lambda: ran.append("late"))
    assert ran == ["late"]
