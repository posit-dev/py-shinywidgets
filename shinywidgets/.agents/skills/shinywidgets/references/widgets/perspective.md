# Perspective (`render_perspective`)

## Overview

`pip install 'shinywidgets[perspective]'`. Give users a Tableau-style
drag-and-drop pivot table over your data, and read back whatever query
they build — WASM-powered, scales to hundreds of thousands of rows with a
flat payload (the browser only queries the visible rows of a server-side
engine, so cost doesn't grow with row count). Accepts a pandas/polars
DataFrame or a `perspective.Table` (both coerced to a
`PerspectiveWidget`), or a `PerspectiveWidget` directly.

## Quick start

```python
import pandas as pd
from shinywidgets import render_perspective

df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})


@render_perspective
def grid():
    return df
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `filter()` | `[[column, op, value], ...]` | `[]` |
| `view_config()` | Dict with `plugin`, `columns`, `group_by`, `split_by`, `split_rollup_mode`, `aggregates`, `sort`, `filter`, `expressions` | seeded at render |

`view_config()` covers only what determines the *rows* shown — cosmetic
changes (opening the settings panel, switching the theme) don't re-fire
it. Exclude `plugin` before reproducing the rows:
`widget.table.view(**{k: v for k, v in cfg.items() if k != "plugin"})`.
Row clicks/selections never reach Python. For anything beyond these two
(e.g. `theme`, `title`), use `grid.read(...)` — but unlike the seeded
accessors, a cosmetic trait read this way can be `None` until the first
browser sync, so guard with `req()`.

## Updating in place

`.widget.update()`/`.widget.theme = ...`. Perspective keeps every table it
hosts in memory for the life of the process, so prefer updating the
existing viewer rather than re-rendering: `.widget.update(df)` appends (or
upserts, for a table with an `index`); `.widget.clear()` then
`.widget.update(df)` swaps rows out entirely (`.widget.replace()` also
swaps rows but doesn't accept a DataFrame).

```python
from shiny import reactive


@reactive.effect
def _stream_rows():
    grid.widget.update(new_rows_df)
```

## Gotchas

- **A viewer's browser can list, read, and write every table on its
  widget's Perspective server.** A table built from a plain DataFrame gets
  its own server (other sessions can't reach it), but a table made with
  `perspective.table()` or `PerspectiveWidget(df)` lives on Perspective's
  process-wide server, reachable by every session — only use that path for
  data every user may see and edit. For per-user data, create the table on
  a private server: `perspective.Server().new_local_client().table(df)`.
- `.widget.replace()` is broken upstream for some inputs — prefer
  `clear()` + `update(df)`.

**More:** <https://shinywidgets.org/widgets/perspective/>
