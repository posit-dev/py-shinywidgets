from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol, cast

from ipywidgets import Widget, widget_serialization

__all__ = (
    "DependencyAdapter",
    "DependencySnapshot",
    "ScalarDependencyAdapter",
    "dependencies",
    "references",
    "register_serializer_adapter",
    "unreachable",
)


def references(value: object) -> frozenset[Widget]:
    """
    The actual widget objects contained in a materialized trait value.

    Only supported widget serialization containers (dict values, lists, and
    tuples) are inspected. Dictionary keys and arbitrary application object
    attributes are not; literal strings that look like model IDs are not
    references.
    """
    found: set[Widget] = set()
    pending: list[object] = [value]
    visited: set[int] = set()
    while pending:
        item = pending.pop()
        if isinstance(item, Widget):
            found.add(item)
        elif isinstance(item, (dict, list, tuple)):
            identity = id(item)
            if identity in visited:
                continue
            visited.add(identity)
            if isinstance(item, dict):
                pending.extend(cast(dict[object, object], item).values())
            else:
                pending.extend(cast(list[object] | tuple[object, ...], item))
    return frozenset(found)


def unreachable(
    roots: Iterable[str],
    graph: Mapping[str, frozenset[str]],
) -> frozenset[str]:
    """
    The graph nodes that cannot be reached from any root. Traversal
    accommodates cycles (mark/sweep); reference counting alone would not.
    """
    reachable: set[str] = set()
    pending = list(roots)
    while pending:
        model_id = pending.pop()
        if model_id in reachable:
            continue
        reachable.add(model_id)
        pending.extend(graph.get(model_id, frozenset()))
    return frozenset(set(graph) - reachable)


@dataclass(frozen=True)
class DependencySnapshot:
    widgets: frozenset[Widget]
    opaque_traits: frozenset[str]

    @property
    def complete(self) -> bool:
        return not self.opaque_traits


class DependencyAdapter(Protocol):
    """
    Supplies the widget dependencies hidden behind a custom trait serializer.

    An adapter must return every widget dependency hidden by that serializer.
    """

    def dependencies(
        self, widget: Widget, trait_name: str, value: object
    ) -> frozenset[Widget]: ...


class ScalarDependencyAdapter:
    """
    Adapter for serializers whose inspected implementation cannot contain
    widget references (e.g., dates, plotly figure values, bokeh bundles).
    """

    def dependencies(
        self, widget: Widget, trait_name: str, value: object
    ) -> frozenset[Widget]:
        return frozenset()


def register_serializer_adapter(
    serializer: Callable[..., object], adapter: DependencyAdapter
) -> None:
    _serializer_adapters[serializer] = adapter


def dependencies(widget: Widget) -> DependencySnapshot:
    """
    Snapshot the widget's materialized dependencies.

    Synced traits without a materialized value are skipped (`trait_has_value`
    is checked before `getattr`), so lazy default factories never run as a
    side effect of collection. Serializers, `get_state()`, and
    `_repr_mimebundle_()` are never called. Traits with an unknown custom
    serializer are reported opaque unless an adapter supplies their
    dependencies.
    """
    ensure_default_adapters()
    found: set[Widget] = set()
    opaque: set[str] = set()
    traits = widget.traits()
    for name in widget.keys:
        if not widget.trait_has_value(name):
            continue
        value = getattr(widget, name)
        serializer = traits[name].metadata.get("to_json")
        if serializer is None or serializer is widget_serialization["to_json"]:
            found.update(references(value))
            continue
        adapter = _serializer_adapters.get(serializer)
        if adapter is None:
            opaque.add(name)
        else:
            found.update(adapter.dependencies(widget, name, value))
    return DependencySnapshot(widgets=frozenset(found), opaque_traits=frozenset(opaque))


_serializer_adapters: dict[Callable[..., object], DependencyAdapter] = {}
_default_adapters_registered = False


def ensure_default_adapters() -> None:
    """
    Register scalar adapters for supported packages' verified serializers.

    Registration is lazy so importing shinywidgets doesn't import heavy
    optional packages. A serializer is only registered after its actual
    implementation has been inspected and found incapable of referencing
    widgets.
    """
    global _default_adapters_registered
    if _default_adapters_registered:
        return
    _default_adapters_registered = True

    scalar = ScalarDependencyAdapter()

    # ipywidgets date traits serialize plain datetime objects.
    from ipywidgets.widgets.trait_types import date_to_json

    register_serializer_adapter(date_to_json, scalar)

    try:
        # plotly figure values serialize plotly graph objects/numpy arrays;
        # the figure schema cannot contain ipywidgets.
        from plotly.serializers import _py_to_js
    except ImportError:
        pass
    else:
        register_serializer_adapter(_py_to_js, scalar)

    try:
        # jupyter_bokeh's render_bundle trait serializes a bokeh RenderBundle
        # to plain JSON; bokeh models are not ipywidgets.
        from jupyter_bokeh.widgets import BokehModel
    except ImportError:
        pass
    else:
        serializer = BokehModel.class_traits()["render_bundle"].metadata.get(
            "to_json"
        )
        if serializer is not None:
            register_serializer_adapter(serializer, scalar)
