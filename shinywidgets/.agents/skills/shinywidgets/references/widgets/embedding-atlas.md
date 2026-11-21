# Embedding Atlas (`render_embedding_atlas`)

## Overview

`pip install 'shinywidgets[embedding_atlas]'` (needs Python 3.11+). A full
embedding explorer — GPU map, auto-generated per-column charts, a
searchable table, and SQL cross-filtering — behind one accessor pair. Built
for thousands to millions of rows. Unlike other renderers, a bare data
frame isn't enough: construct the widget yourself, naming the embedding
columns:

```python
import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shinywidgets import render_embedding_atlas

df = pd.DataFrame(
    {"x": [0.0, 1.0, 0.1], "y": [0.0, 1.0, 0.2], "text": ["alpha", "beta", "gamma"]}
)


@render_embedding_atlas
def atlas():
    return EmbeddingAtlasWidget(df, x="x", y="y", text="text")
```

The embedding (scatter) view needs a browser with WebGPU and its
`shader-f16` feature (recent Chrome/Edge/Firefox); elsewhere the rest of the
explorer still works. In a non-filling layout, give the output a height of
at least `"600px"`.

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `predicate()` | The current cross-filter as a DuckDB SQL boolean expression, or `None` | `None` |
| `selected_rows()` | Rows passing the filter, as the same frame type the widget was built from, plus a `__row_index__` column | all rows (nothing filtered) |

Built from every chart's clicks/brushes and the embedding view's lasso.
Both debounced 250ms by default. `selected_rows()` runs a DuckDB query per
call — read it in a `@reactive.calc` when several outputs need it.

## Updating in place

None — the explorer doesn't respond to trait changes from Python at all;
to change it, re-render. Round-trip a saved filter state across a
re-render if you need to soften the reset.

## Gotchas

- **Security**: the explorer runs browser-sent SQL against the widget's own
  DuckDB connection. By default the renderer locks it down
  (`enable_external_access = false`, `lock_configuration = true`) so only
  the data you gave the widget is reachable; pass
  `allow_unrestricted_connection=True` only for a local, single-user app.
  Even locked down, a visitor can still send expensive queries that block
  the Python process while they run.
- A bare data frame return doesn't build the widget — you must construct
  `EmbeddingAtlasWidget(df, x=..., y=..., text=...)` yourself.

**More:** <https://shinywidgets.org/widgets/embedding-atlas/>
