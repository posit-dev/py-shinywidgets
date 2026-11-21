# Mosaic (`render_mosaic_widget`)

## Overview

`pip install 'shinywidgets[mosaic_widget]'`. Crossfilter millions of rows
in Shiny, with every query running in DuckDB instead of the browser —
several linked charts/tables driven by one Mosaic spec, not a single view.
Return a `mosaic_widget.MosaicWidget` built from a spec and the data to
register:

```python
import pandas as pd
from mosaic_widget import MosaicWidget
from shinywidgets import render_mosaic_widget

penguins = pd.DataFrame({"species": ["Adelie", "Gentoo"], "body_mass": [3700, 5000]})

spec = {
    "plot": [
        {"mark": "dot", "data": {"from": "penguins"}, "x": "species", "y": "body_mass"}
    ],
    "width": 600,
    "height": 300,
}


@render_mosaic_widget
def dashboard():
    return MosaicWidget(spec, data={"penguins": penguins})
```

Mosaic specs set each plot's pixel size, so plots keep that size while the
output itself fills its container (or takes an explicit `height`) — a
smaller explicit height makes the plots overflow visibly, not clip.

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `params()` | `{name: {"value": ..., "predicate": ...}}` per declared selection | `{}` until the spec loads; null `value` per un-brushed selection |
| `data(table=None, *, filter_by=None)` | Rows matching current selections, as a lazy DuckDB relation | — |

`params()` is debounced 250ms by default while dragging. `data()` re-reads
whenever `params()` changes and runs the query on each read — call it once
in a `@reactive.calc`. `table` may be omitted when the spec registers
exactly one data source; `filter_by` defaults to every active selection.
`data()` queries the widget's *live* params trait, which can briefly lead
`params()`'s debounced value during a settling brush.

## Updating in place

Assign a new spec to `.widget.spec` (resets current selections) rather than
re-rendering — each re-render creates a new `MosaicWidget`, a new DuckDB
connection, and re-sends the JS bundle. `.widget.params` is read-only in
practice: assigning it does nothing in the browser.

```python
from shiny import reactive


@reactive.effect
def _restyle():
    dashboard.widget.spec = new_spec
```

## Gotchas

- **Security**: Mosaic runs browser-sent SQL against the widget's
  connection. By default the renderer locks it down
  (`enable_external_access = false`, `lock_configuration = true`); pass
  `allow_unrestricted_connection=True` only for a local, single-user app.
- **For a *shared* connection** (`con=`, or a `duckdb` relation in `data=`
  landing on `duckdb.default_connection()`), the lockdown is **permanent
  and database-wide** — it locks every other cursor on that connection too,
  not just the widget's. Do any server-side file reads
  (`read_parquet()`, etc.) on that connection *before* the first render, or
  opt out for it.
- DataFrames passed as `data=` get a fresh in-memory connection per widget
  (session-isolated); a shared `con=` means every session's registered
  table under the same name replaces another's — only share a connection
  for data that's identical across users.

**More:** <https://shinywidgets.org/widgets/mosaic/>
