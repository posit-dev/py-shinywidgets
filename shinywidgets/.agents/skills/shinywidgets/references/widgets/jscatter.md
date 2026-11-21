# jscatter (`render_jscatter`)

## Overview

`pip install 'shinywidgets[jscatter]'`. GPU-accelerated scatter plots for
millions of points, with lasso selection that comes back to Python. Accepts
a `jscatter.Scatter` (coerced to `JupyterScatter`) or a `JupyterScatter`
widget directly. The lightest bundle of the GPU scatter renderers — prefer
it over plotly/lonboard for a few hundred thousand points unless you
specifically need lonboard's map projections or plotly's broader chart-type
ecosystem. One upstream limit: only two of color/size/opacity can combine
on one chart.

## Quick start

```python
import pandas as pd
from jscatter import Scatter
from shinywidgets import render_jscatter

df = pd.DataFrame({"x": [1, 2, 3], "y": [1, 4, 9]})


@render_jscatter
def plot():
    return Scatter(data=df, x="x", y="y")
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `selected()` | `numpy.ndarray` (uint32) of selected row *positions* | empty array (cancels — like `.widget` — until the browser's first report) |
| `selected_rows(df=None)` | Rows of `df` (or the `Scatter`'s own data) at the selected positions | empty frame |

From a lasso or single click. `selected_rows()`'s `df` defaults to the
frame the `Scatter` was built with; pass it explicitly when the render
function returns a bare `JupyterScatter` (which retains no frame). The
match is positional — after a re-render or in-place data replacement with
different rows, a retained position can point at a different row; carry an
ID column if the data can change. For index labels instead of positions
(with `data_use_index=True`), use `plot.value.selection()`. Other traits
worth reading with `plot.read(...)`: `"hovering"` (hovered point's row
position), `"zoom_level"`, `"lasso_selection_polygon"`.

## Updating in place

Use `.widget` to mutate the rendered plot — a method on `plot.value` or a
trait on `.widget`, wrapped in `reactive.isolate()` when the write would
otherwise re-trigger the same effect:

```python
from shiny import reactive

@reactive.effect
def _recolor():
    with reactive.isolate():
        plot.widget.color = new_colors
```

## Gotchas

- **Selecting more than ~3 million points sends a message larger than the
  default 16 MiB websocket limit** — dropped client-side (the session
  stays connected, but the selection is lost and the user sees a sticky
  error notification). Raise it with `shiny run --ws-max-size` and set
  `SHINYWIDGETS_WS_MAX_SIZE` to match.
- The plot resizes to fit its output unless it has its own height set
  (jupyter-scatter's default of 240 doesn't count as "set" — ask for a
  slightly different number, e.g. 241, if you want a genuinely fixed size
  at that value).

**More:** <https://shinywidgets.org/widgets/jscatter/>
