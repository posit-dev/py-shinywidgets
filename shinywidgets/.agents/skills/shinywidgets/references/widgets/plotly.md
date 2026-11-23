# Plotly (`render_plotly`)

## Overview

`pip install 'shinywidgets[plotly]'`. The richest accessor set in the whole
roster — clicks, hover, box/lasso selection, zoom/pan, legend toggles — all
flow back to Python with no JavaScript. Returns a `go.Figure` (coerced to a
`FigureWidget`) or a `FigureWidget` directly, or a Dash-style `(figure,
config)` tuple. Don't read `input.*()` inside the render function to react
to a click or selection — read the accessor instead and mutate `.widget`
from an effect (see "Updating in place" below).

## Quick start

```python
import plotly.express as px
from shinywidgets import render_plotly

df = px.data.iris()


@render_plotly
def plot():
    return px.scatter(df, x="sepal_width", y="sepal_length")
```

## Accessors

Every accessor returns `None` until the interaction happens — check with
`req(pts is not None)`, not `req(pts)` (a DataFrame has no truth value).
`selected()`, `selecting()`, and `hover()` are opt-in: pass
`listen_to=["selected", "hover"]` to the decorator (their payloads grow
with the selection, or stream continuously); reading an undeclared one
raises.

| Accessor | Returns | Before first interaction |
|---|---|---|
| `clicked()` | DataFrame, one row per clicked point | `None` |
| `selected()` | DataFrame of points in a box/lasso selection (opt-in) | `None` |
| `selecting()` | Like `selected()`, live while dragging (opt-in, debounced 250ms) | `None` |
| `brushed()` | `{"range": {...}}` or `{"lassoPoints": {...}}` region dict | `None` |
| `brushing()` | Like `brushed()`, live while dragging (debounced 250ms) | `None` |
| `relayout()` | Axis-range delta from the most recent zoom/pan/autoscale | `None` |
| `hover()` | DataFrame of points under the mouse (opt-in, debounced 250ms) | `None` |
| `double_clicked()` | `True`/`None` pulse on every double-click | `None` |
| `legend_clicked()` | DataFrame of traces affected by the last legend click | `None` |
| `visible_traces()` | DataFrame of every trace's current visibility | seeded from the figure |
| `selected_rows(df)` | Rows of `df` the user selected | empty DataFrame |

`selected_rows(df, *, key=None)` needs each point to carry its row's
identity as `customdata`: `px.scatter(df, ..., custom_data=[df.index])`
matches by `df`'s index label (works on a filtered/sorted `df` too); for a
non-pandas frame, pass `custom_data=["id"]` with `key="id"`.

A double-click on the plot background clears `clicked()` and the selection
accessors; a double-click on a marker re-fires the click, leaving it
unchanged. Clicking the same point twice doesn't re-fire. Across a
re-render, `clicked()`/`hover()`/`relayout()`/etc. keep their last value,
but `selected()`/`brushed()`/`visible_traces()` re-seed from the new plot.
A kept `point_index` can point at a different point after a re-render with
new data — key lookups off `customdata` instead.

## Updating in place

Read inputs under `reactive.isolate()` in the render function, then mutate
`.widget` in a `@reactive.effect` — use `.widget.batch_update()` for several
changes at once:

```python
from shiny import reactive, req


@reactive.effect
def _highlight():
    pts = plot.clicked()
    req(pts is not None)
    with plot.widget.batch_update():
        plot.widget.layout.title.text = f"Clicked x={pts['x'].iloc[0]}"
```

## Gotchas

- **Large selections**: for big data, don't opt into `selected()` — read
  `brushed()` and filter your own frame instead (a box is a range filter; a
  lasso is a point-in-polygon test over `lassoPoints`).
- **Height**: a figure with explicit `layout.height` keeps that height.
  For a plot that fills a fixed-height container, pass
  `output_widget("id", height="450px", fillable=True)` — without
  `fillable=True` plotly falls back to its own 360px default regardless of
  the output's height.
- **An update over the websocket limit (16 MiB default) is dropped
  client-side** with an error logged to the browser console, not a crash.
  Raise it with `shiny run --ws-max-size <bytes>` and set
  `SHINYWIDGETS_WS_MAX_SIZE` to match.
- Plotly.py's own native events (`on_click()`, etc.) are muted by default
  and un-mute automatically once you register one, in the render function or
  later. Turn them on app-wide with `shinywidgets.config(native_events=True)`
  for `.widget.data[i].selectedpoints` reads, a callback on a trace added
  after render, or a widget shared across sessions.

**More:** <https://shinywidgets.org/widgets/plotly/>

Written against `plotly` 6.x.
