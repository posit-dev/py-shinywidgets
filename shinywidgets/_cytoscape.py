"""
Accessors for `render_ipycytoscape`.

The click accessors are backed by the widget's interaction handlers
(`CytoscapeWidget.on()`); the selection accessors observe the `selected`
trait on the graph's child Node/Edge widgets.

All specs are eager. The click specs must be: ipycytoscape's frontend wires
up only the event types it knows when the view is created, so a handler
registered on first read (after the view exists) would be silently dropped.
The selection specs are eager by the state-kind default, which their attach
satisfies by seeding from the children's current `selected` traits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List

from ._accessors import AccessorSpec, Attach, Emit

if TYPE_CHECKING:
    from ipycytoscape import CytoscapeWidget


def attach_clicked(element: str) -> Attach:
    def attach(widget: CytoscapeWidget, emit: Emit) -> Callable[[], None]:
        # The frontend calls the handler with the clicked element's
        # ele.json() dict
        widget.on(element, "click", emit)
        return lambda: widget.on(element, "click", emit, remove=True)

    return attach


NODE_CLICKED = AccessorSpec(
    name="node_clicked", kind="event", attach=attach_clicked("node"), eager=True
)
EDGE_CLICKED = AccessorSpec(
    name="edge_clicked", kind="event", attach=attach_clicked("edge"), eager=True
)


def attach_selected(element: str) -> Attach:
    def attach(widget: CytoscapeWidget, emit: Emit) -> Callable[[], None]:
        # A snapshot: children added to the graph after attach (i.e. after
        # the render) aren't observed until the next render re-attaches
        children = tuple(
            widget.graph.nodes if element == "node" else widget.graph.edges
        )

        def selected_data() -> List[Dict[str, Any]]:
            return [child.data for child in children if child.selected]

        def on_change(change: object) -> None:
            emit(selected_data())

        for child in children:
            child.observe(on_change, "selected")
        emit(selected_data())  # seed the current selection

        def detach() -> None:
            for child in children:
                child.unobserve(on_change, "selected")

        return detach

    return attach


# A box-select changes many children's `selected` in a burst, hence the
# debounce default
SELECTED_NODES = AccessorSpec(
    name="selected_nodes",
    kind="state",
    attach=attach_selected("node"),
    rate_policy="debounce",
)
SELECTED_EDGES = AccessorSpec(
    name="selected_edges",
    kind="state",
    attach=attach_selected("edge"),
    rate_policy="debounce",
)

CYTOSCAPE_ACCESSORS = (NODE_CLICKED, EDGE_CLICKED, SELECTED_NODES, SELECTED_EDGES)
