# PyGWalker (`render_pygwalker`)

## Overview

`pip install 'shinywidgets[pygwalker]' duckdb sqlglot`. Give users a
Tableau-style drag-and-drop explorer over any pandas (or polars, with
pygwalker >= 0.6) DataFrame, computed server-side — cost stays flat whether
the frame has 500 or 1,000,000 rows. Accepts a plain DataFrame (coerced
automatically) or a widget from `pygwalker.api.anywidget.walk()` (use this
to pass options like `theme_key`). **Don't use top-level `pygwalker.walk()`**
outside Jupyter — it starts a blocking web server instead of returning a
widget.

## Quick start

```python
import duckdb
import pandas as pd
import pygwalker
from shinywidgets import render_pygwalker

# Required before rendering (see Security below)
duckdb.execute("SET TimeZone = 'UTC'")
duckdb.execute("SET enable_external_access = false")
duckdb.execute("SET lock_configuration = true")

pygwalker.GlobalVarManager.set_privacy("offline")

df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})


@render_pygwalker
def walker():
    return df
```

Outside filling layouts, give it a height that fits PyGWalker's UI (e.g.
`"800px"`).

## Accessors

None — the widget has no traits that track the explorer's state, so
there's nothing to read reactively. For save/export events, use
`widget.on_msg` registered on the rendered widget.

## Updating in place

None — changing the explorer means re-rendering it, which re-sends
PyGWalker's large JS bundle. Avoid unnecessary re-renders.

## Gotchas

- **Security (required)**: PyGWalker computes charts by running
  browser-sent SQL on DuckDB's process-wide *default* connection — this
  renderer **raises** unless that connection is locked down first (as in
  the Quick start above). `lock_configuration` is permanent for the
  connection, so set anything else you need (`SET memory_limit = ...`)
  before it. Even locked down, every PyGWalker widget in the process shares
  one connection and table name — per-user data is kept apart only by each
  request re-registering its own data right before it queries, not a hard
  boundary. A visitor can still send expensive queries that block every
  session's Python process while they run. For mutually private datasets
  across users, prefer a renderer that keeps data apart by design.
- **Privacy**: by default PyGWalker sends usage events and checks for
  updates from both server and browser. Call
  `pygwalker.GlobalVarManager.set_privacy("offline")` before rendering to
  disable both.
- polars DataFrames need pygwalker >= 0.6 — older releases raise a `TypeError`
  pointing at `df.to_pandas()`.

**More:** <https://shinywidgets.org/widgets/pygwalker/>
