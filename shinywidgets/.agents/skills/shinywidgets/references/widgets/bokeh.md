# Bokeh (`render_bokeh`)

## Overview

`pip install 'shinywidgets[bokeh]'`. For plots built from live Python
objects (a `ColumnDataSource` you mutate directly) that need two-way sync.
Returns a bokeh model (e.g. a `figure`, coerced to a `jupyter_bokeh.BokehModel`)
or a `BokehModel` directly. Create bokeh models per session (inside the
render function) — not at the top level of a Shiny Core app, where every
visitor would share them. Plots that share a `ColumnDataSource` for linked
selection must be returned together, in one layout, from a single render
function.

## Quick start

```python
from bokeh.plotting import figure
from shinywidgets import render_bokeh

@render_bokeh
def plot():
    p = figure()
    p.line([1, 2, 3], [1, 4, 9])
    return p
```

A `figure` fills its output by default (`sizing_mode="stretch_both"`)
unless it has an explicit `width`, `height`, `sizing_mode`, or
`aspect_ratio`.

## Accessors

Bokeh model properties aren't widget traits, so `reactive_read()` can't see
them — read these instead.

| Accessor | Returns | Before first interaction |
|---|---|---|
| `selected()` | Row indices into the plot's `ColumnDataSource` | `[]` (seeded with the current selection at render) |
| `selected_rows()` | The selected rows as a pandas DataFrame | empty DataFrame |
| `tapped()` | A `bokeh.events.Tap` (`.x`, `.y` in data units) | `None` |
| `zoomed()` | A `bokeh.events.RangesUpdate` (`.x0`, `.x1`, `.y0`, `.y1`) | seeded from current ranges (or `None` for an auto-fitting/categorical range) |

`selected()`/`selected_rows()` need a plot (or layout) with exactly one
`ColumnDataSource`, and are debounced 250ms by default. `selected()`'s
indices are positions — after a re-render or an in-place `source.data`
replacement with new rows, a retained index can point at a different row;
carry an ID column and map through it if you need to track rows across
data changes. For anything else, bokeh's own callbacks
(`source.selected.on_change("indices", ...)`) work too and may set
`reactive.value`s.

## Updating in place

Modify the bokeh models in place (e.g. `source.data = ...`) rather than
re-rendering:

```python
from shiny import reactive

@reactive.effect
def _update_source():
    source.data = dict(x=new_x, y=new_y)
```

## Gotchas

- **Raw `on_change`/`on_event` callbacks you register yourself fire twice
  per browser change** — the accessors already dedupe this for you.
- Build models per session; a module-level bokeh object in Shiny Core is
  shared (and mutated) by every visitor.

**More:** <https://shinywidgets.org/widgets/bokeh/>
