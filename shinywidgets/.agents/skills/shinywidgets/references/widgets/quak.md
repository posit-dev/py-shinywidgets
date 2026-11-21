# quak (`render_quak`)

## Overview

`pip install 'shinywidgets[quak]'`. Browse millions of rows with
per-column histograms, no app code required — a 5M-row table paints like
5k because only on-screen rows plus histogram bins cross the wire. Accepts
a DataFrame-like object (pandas, polars, pyarrow `Table` — coerced to a
`quak.Widget`) or a `quak.Widget` directly.

## Quick start

```python
import pandas as pd
from shinywidgets import render_quak

df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})


@render_quak
def table():
    return df
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `sql()` | The SQL query for the table's current sort/filter state | cancels while the table initializes |
| `data()` | Rows matching the current state, as a lazy DuckDB relation | — |

Brushing a column histogram or sorting updates `sql()`, debounced 250ms by
default. `data()` re-reads whenever `sql()` changes and runs the query on
each read — call it once in a `@reactive.calc` and share the result rather
than calling it from several outputs. `sql()` is read-only: setting it from
Python doesn't change the table.

## Updating in place

Use `.widget` to mutate the rendered table (layout only — `.layout.height`
works; the `sql` trait itself is read-only from Python, so a data change
still needs a re-render).

## Gotchas

- **Security**: quak runs browser-sent SQL against the widget's DuckDB
  connection. By default the renderer locks it down
  (`enable_external_access = false`, `lock_configuration = true`); pass
  `allow_unrestricted_connection=True` only for a local, single-user app.
  If you build the `quak.Widget` yourself from your own DuckDB connection
  (`quak.Widget(con)`), the lockdown is permanent and database-wide — do any
  server-side file reads on that connection *before* the first render, or
  opt out for it.
- Even locked down, a visitor can still send expensive queries that block
  the Python process while they run.

**More:** <https://shinywidgets.org/widgets/quak/>
