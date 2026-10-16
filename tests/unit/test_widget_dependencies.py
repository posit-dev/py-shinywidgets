from __future__ import annotations

from ipywidgets import HTML, Box, Widget, widget_serialization
from shiny import Session
from shiny.session import session_context
from traitlets import Any, default

from shinywidgets._widget_dependencies import (
    DependencyAdapter,
    dependencies,
    references,
    register_serializer_adapter,
)


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
