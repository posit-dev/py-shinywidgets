# ipycytoscape (`render_ipycytoscape`)

## Overview

`pip install 'shinywidgets[ipycytoscape]'`. Turn a networkx graph into an
interactive, clickable network, with communities, shortest paths, and
precise CSS-like styling computed in Python. Accepts a `networkx.Graph`
(coerced to a `CytoscapeWidget`) or a `CytoscapeWidget` directly.
Comfortable into the low thousands of nodes — every node and edge is its
own ipywidgets model, so render time scales with element count; for tens
of thousands of nodes, prefer [ipysigma](ipysigma.md).

## Quick start

```python
import networkx as nx
from shinywidgets import render_ipycytoscape


@render_ipycytoscape
def graph():
    return nx.karate_club_graph()
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `clicked_node()` | Clicked node's cytoscape `ele.json()` dict (`"data"` holds `"id"`) | `None` |
| `clicked_edge()` | Clicked edge's `ele.json()` dict (`"source"`, `"target"`) | `None` |
| `selected_nodes()` | Selected nodes' data dicts, in graph order | `[]` |
| `selected_edges()` | Selected edges' data dicts, in graph order | `[]` |

`clicked_*()` are kept across re-renders (a retained payload's id may not
exist in the new graph). `selected_*()` cover box/multi-select and don't
reset on re-render; debounced 250ms by default. **ipycytoscape makes nodes
unselectable by default** — create the widget with `auto_unselectify=False`
and set `selectable = True` on each node (plus `box_selection_enabled=True`
for shift-drag selection) to populate `selected_nodes()`. For other event
types, register `CytoscapeWidget.on()` callbacks inside the render
function and set a `reactive.value` from them.

## Updating in place

Use `.widget` — `.widget.set_style()`, `.widget.set_layout()`, or setting
`classes` on nodes in `.widget.graph.nodes` — without re-rendering:

```python
from shiny import reactive


@reactive.effect
def _restyle():
    graph.widget.set_style(new_stylesheet)
```

## Gotchas

- **Removing a node from Python can corrupt the rest of the graph**
  (upstream bug) — prefer re-rendering a graph if nodes need to be removed.
- **Position/zoom/pan never sync browser to Python.**
- Lightly maintained upstream (last PyPI release in 2022) — verify
  behavior against the version you pin.
- Doesn't re-run its own graph layout on a card resize, so a large
  resize can leave part of the graph outside the visible area.

**More:** <https://shinywidgets.org/widgets/ipycytoscape/>

Written against `ipycytoscape` 1.x.
