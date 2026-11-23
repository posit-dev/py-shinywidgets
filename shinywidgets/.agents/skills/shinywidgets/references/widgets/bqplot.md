# bqplot (`render_bqplot`)

## Overview

`pip install 'shinywidgets[bqplot]'`. Grammar-of-graphics plots where every
selection, brush, and drag feeds straight back into Python, animating data
updates in place. Accepts a `bqplot.Figure`, including one built through
`bqplot.pyplot`. No `clicked()` accessor by design — the figure's own
interaction overlay would swallow it; use click-select (below) instead.

## Quick start

```python
import bqplot.pyplot as bplt
from shinywidgets import render_bqplot


@render_bqplot
def fig():
    fig = bplt.figure()  # always call figure() explicitly inside the render fn
    bplt.plot([1, 2, 3], [1, 4, 9])
    return fig
```

With `bqplot.pyplot`, always start the render function with
`fig = bplt.figure(...)` — pyplot's "current figure" is process-global, so
plotting without an explicit `figure()` call reuses one figure across
renders, outputs, and sessions, and fails after the first re-render.

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `selected()` | List aligned with `fig.marks`; each entry a `numpy.ndarray` of selected element indices, or `None` | `None` per unselected mark |
| `brush()` | The current brush region (shape depends on selector type) | `None` (also `None` if `interaction` isn't a brush selector) |
| `selected_rows(df, mark=None)` | Rows of `df` at the selected positions of one mark | empty frame |

Set via a brush/lasso `bqplot.interacts.Selector` (the figure's
`interaction`) or click-select (`interactions={"click": "select"}`).
Single-mark figures read `fig.selected()[0]`. Both are debounced 250ms by
default. Indices/positions are into the mark's data — after in-place data
replacement (`mark.x = ...`) or a re-render, a retained index can point at
a different element; key lookups by ID rather than position when the data
can change. `selected_rows()`'s `mark` may be omitted with exactly one
mark. To react to one mark's selection specifically,
`reactive_read(fig.widget.marks[0], "selected")` remains available.

## Updating in place

Use `.widget` to mutate the rendered figure — a mark's or scale's traits —
in place; changes are synced and animated (`fig.widget.animation_duration`
tweens the transition):

```python
from shiny import reactive


@reactive.effect
def _update_line():
    fig.widget.marks[0].y = new_y
```

## Gotchas

- **Sharing one `Selector` object across marks that belong to two
  separately-rendered `Figure`s fails outright** in this frontend
  (`Could not create a view for model id ...`) — link two bqplot figures
  with the Python round-trip instead (read one mark's `selected()`, write
  the other mark's `.selected` trait), not bqplot's own shared-`Selector`
  notebook idiom.
- The figure's built-in toolbar (`display_toolbar=True`) works; the active
  `PanZoom` is readable with `fig.read("interaction")`.

**More:** <https://shinywidgets.org/widgets/bqplot/>

Written against `bqplot` 0.x.
