# Observable Plot (`render_obsplot`)

## Overview

`pip install 'shinywidgets[obsplot]'`. Build Observable Plot's concise
grammar-of-graphics charts in Shiny, with browser-native tooltips and
crosshairs. Return the `pyobsplot.widget.ObsplotWidget` that `Plot.plot()`
(or an `Obsplot()` creator) produces — the `Plot`/`Obsplot` object itself
is a plot *creator*, not a chart. Only `format='widget'` (the default)
produces a chart; `'html'`/`'svg'`/`'png'` return `None`, rendering as an
empty output.

## Quick start

```python
import pandas as pd
from pyobsplot import Plot
from shinywidgets import render_obsplot

df = pd.DataFrame({"x": [1, 2, 3], "y": [1, 4, 9]})


@render_obsplot
def plot():
    return Plot.plot({"marks": [Plot.dot(df, {"x": "x", "y": "y"})]})
```

Observable Plot charts have a fixed pixel width: they shrink proportionally
to fit a narrower container but never grow past the specification's width.
Control size with `width`/`height` in the spec itself.

## Accessors

None — pyobsplot's interactions (tips, crosshairs) run entirely in the
browser and nothing syncs back to Python. There's no widget state to
`reactive_read()` either.

## Updating in place

Assign a new specification to `.widget.spec` (the same dict you'd pass to
`Plot.plot()`) to change the chart without re-rendering:

```python
from shiny import reactive


@reactive.effect
def _update_spec():
    plot.widget.spec = {"marks": [Plot.dot(new_df, {"x": "x", "y": "y"})]}
```

## Gotchas

- **pandas/polars `DataFrame`s in the spec are serialized to Arrow IPC and
  sent with the widget state** — a chart over a large dataset makes a
  large message, and pyobsplot's JS bundle is re-sent on each render.
  Aggregate before plotting for large data.

**More:** <https://shinywidgets.org/widgets/obsplot/>

Written against `pyobsplot` 0.x.
