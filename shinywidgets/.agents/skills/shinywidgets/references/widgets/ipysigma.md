# ipysigma (`render_ipysigma`)

## Overview

`pip install 'shinywidgets[ipysigma]'`. Render a networkx graph as a
GPU-accelerated, clickable network explorer (sigma.js) — tens of thousands
of nodes/edges stay smooth where an SVG renderer (ipycytoscape) can't.
Accepts a networkx graph (coerced to a `Sigma` widget with default
options) or a `Sigma` widget directly, the way to customize appearance
(`Sigma(G, node_size=G.degree, node_color="community")`). Also the answer
for pyvis users — larger networks render more smoothly and, being a
widget, report the selected node back to Python.

## Quick start

```python
import networkx as nx
from shinywidgets import render_ipysigma


@render_ipysigma
def sigma():
    return nx.karate_club_graph()
```

In a filling layout the graph fills its container unless given an
explicit `height`/`raw_height` (sigma's own 500px default, or one set
globally with `Sigma.set_defaults(height=...)`, counts as unset).

## Accessors

None named — read interactions with `sigma.read(...)`:
`sigma.read("selected_node")`, `"selected_edge"`, `"camera_state"`,
`"layout"`.

## Updating in place

None — ipysigma only reads its options when the graph is first drawn, so
setting traits on `.widget` afterwards doesn't update the browser. To
change what's shown, re-render, passing forward any state you want to keep
(`layout=`, `camera_state=`) to the new `Sigma`:

```python
@render_ipysigma
def sigma():
    return Sigma(new_graph, camera_state=sigma.read("camera_state"))
```

## Gotchas

- **No Python-to-browser trait sync at all** — this is the one network
  widget in the roster with zero in-place update path; budget for a
  re-render on every change.
- Each `Sigma` view holds 3 WebGL contexts; browsers cap around 16 per
  page, so keep to about 5 ipysigma graphs on one page before older ones
  start going blank.

**More:** <https://shinywidgets.org/widgets/ipysigma/>
