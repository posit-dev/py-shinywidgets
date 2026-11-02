"""
Accessors for `render_ipycytoscape`, backed by the widget's interaction
handlers (`CytoscapeWidget.on()`).

Both specs are eager: ipycytoscape's frontend wires up only the event types it
knows when the view is created, so a handler registered on first read (after
the view exists) would be silently dropped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

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

CYTOSCAPE_ACCESSORS = (NODE_CLICKED, EDGE_CLICKED)
