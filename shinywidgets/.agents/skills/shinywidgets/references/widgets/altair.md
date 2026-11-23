# Altair (`render_altair`)

## Overview

`pip install 'shinywidgets[altair]'`. Declares the selection in Vega-Lite's
own grammar (`alt.selection_interval()`/`selection_point()`), not assembled
from callbacks, so it composes cleanly across layers and facets. Accepts an
`altair.Chart` (coerced to a `JupyterChart`) or a `JupyterChart` directly.
Always name a selection (`name="brush"`) — altair's auto-generated names
change between renders.

## Quick start

```python
import altair as alt
from shiny.express import render
from vega_datasets import data
from shinywidgets import render_altair

cars = data.cars()


@render_altair
def chart():
    brush = alt.selection_interval(name="brush")
    return (
        alt.Chart(cars)
        .mark_point()
        .encode(x="Horsepower", y="Miles_per_Gallon")
        .add_params(brush)
    )


@render.data_frame
def selected_cars():
    return chart.selected_rows("brush")  # empty frame until the user brushes
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `selected(name=None)` | An altair `IntervalSelection`/`PointSelection`/`IndexSelection`; `.value` holds what's selected | an *empty* selection (never `None` — altair reports from the start) |
| `selected_rows(name=None, df=None)` | Rows of `df` in the selection, evaluated like Vega-Lite (binned/temporal fields included) | empty DataFrame |

`name` may be omitted when the chart has exactly one selection. Debounced
250ms by default while dragging. `selected_rows()`'s `df` defaults to the
chart's own data frame; pass it explicitly for a chart whose data is a URL.
A selection spanning several views with *different* data frames returns a
`dict` keyed by view name instead of one frame — give subcharts a `name=`
for readable keys. Prefer declaring selections with `fields=`/`encodings=`:
a bare `alt.selection_point()` selects positional row indices, which can
silently point at different rows after a re-render with new data.

## Updating in place

Selections can't be set from Python, but params can — set
`chart.widget.params.<name> = value` from a `@reactive.effect` to update the
chart without re-sending its data:

```python
from shiny import reactive


@reactive.effect
def _set_threshold():
    chart.widget.params.cutoff = input.cutoff()
```

Prefer this (or a re-render) over replacing `chart.widget.chart`, which
re-sends the data and replaces `chart.widget.selections`/`.params` with new
objects — any observer registered on the old ones silently stops firing.

## Gotchas

- **Offline use**: `JupyterChart` loads its JS from a CDN by default; call
  `alt.JupyterChart.enable_offline()` (requires `vl-convert-python`) for
  apps without internet access.
- Two Vega-Lite selections sharing one view clear each other — a legend
  click can clear a brush.
- `selected_rows()` only matches layers that share the *identical*
  underlying frame object, not merely an equal one — `alt.Chart(df.copy())`
  per layer breaks it.
- A chart with no explicit width/height fills its container; concatenated,
  faceted, and repeated charts keep their natural size instead.

**More:** <https://shinywidgets.org/widgets/altair/>

Written against `altair` 6.x.
