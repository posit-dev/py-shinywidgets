"""
Accessors for `render_ipycytoscape`.

The click accessors are backed by the widget's interaction handlers
(`CytoscapeWidget.on()`); the selection accessors observe the `selected`
trait on the graph's child Node/Edge widgets, plus the graph's
nodes/edges list traits so membership and order changes republish.

All specs are eager. The click specs must be: ipycytoscape's frontend wires
up only the event types it knows when the view is created, so a handler
registered on first read (after the view exists) would be silently dropped.
The selection specs are eager by the state-kind default, which their attach
satisfies by seeding from the children's current `selected` traits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, FrozenSet, List, Tuple, Union

from ._accessors import AccessorSpec, Attach, Emit

if TYPE_CHECKING:
    from ipycytoscape import CytoscapeWidget, Edge, Node

    Element = Union[Node, Edge]
    # What the selection specs emit: the graph's children in order, and the
    # selected subset. The user-facing data list is built from this by the
    # spec's payload, once per publication.
    SelectionRaw = Tuple[Tuple[Element, ...], FrozenSet[Element]]


def attach_clicked(element: str) -> Attach:
    def attach(widget: CytoscapeWidget, emit: Emit) -> Callable[[], None]:
        # The frontend calls the handler with the clicked element's
        # ele.json() dict
        widget.on(element, "click", emit)
        return lambda: widget.on(element, "click", emit, remove=True)

    return attach


CLICKED_NODE = AccessorSpec(
    name="clicked_node", kind="state", attach=attach_clicked("node")
)
CLICKED_EDGE = AccessorSpec(
    name="clicked_edge", kind="state", attach=attach_clicked("edge")
)


def attach_selected(element: str) -> Attach:
    trait = "nodes" if element == "node" else "edges"

    def attach(widget: CytoscapeWidget, emit: Emit) -> Callable[[], None]:
        graph = widget.graph
        order: Tuple[Element, ...] = tuple(getattr(graph, trait))
        selected = {child for child in order if child.selected}
        observed = set(order)

        # A box-select toggles many children's `selected` in a burst, so each
        # notification only maintains the set (O(1) per toggle) and emits a
        # cheap raw; the graph-ordered data list is the payload's job
        def on_selected(change: Any) -> None:
            child = change["owner"]
            if change["new"]:
                selected.add(child)
            else:
                selected.discard(child)
            emit((order, frozenset(selected)))

        # ipycytoscape's nodes/edges are spectate MutableLists, so in-place
        # add/remove/reorder fires this too
        def on_membership(change: Any) -> None:
            nonlocal order, selected, observed
            order = tuple(getattr(graph, trait))
            current = set(order)
            for child in observed - current:
                child.unobserve(on_selected, "selected")
            for child in current - observed:
                child.observe(on_selected, "selected")
            observed = current
            selected = {child for child in order if child.selected}
            emit((order, frozenset(selected)))

        for child in order:
            child.observe(on_selected, "selected")
        graph.observe(on_membership, trait)
        emit((order, frozenset(selected)))  # seed the current selection

        def detach() -> None:
            graph.unobserve(on_membership, trait)
            for child in observed:
                child.unobserve(on_selected, "selected")

        return detach

    return attach


def selected_data(raw: SelectionRaw) -> List[Dict[str, Any]]:
    order, selected = raw
    return [child.data for child in order if child in selected]


# A box-select changes many children's `selected` in a burst, hence the
# debounce default
SELECTED_NODES = AccessorSpec(
    name="selected_nodes",
    kind="state",
    attach=attach_selected("node"),
    payload=selected_data,
    rate_policy="debounce",
)
SELECTED_EDGES = AccessorSpec(
    name="selected_edges",
    kind="state",
    attach=attach_selected("edge"),
    payload=selected_data,
    rate_policy="debounce",
)

CYTOSCAPE_ACCESSORS = (CLICKED_NODE, CLICKED_EDGE, SELECTED_NODES, SELECTED_EDGES)
