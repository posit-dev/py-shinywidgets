# itables (`render_itables`)

## Overview

`pip install 'shinywidgets[itables]'`. Turn a pandas or polars data frame
into a searchable, sortable, exportable DataTable with zero configuration —
no extra app code, no `shinywidgets[...]` row-selection wiring. Returns an
`itables.widget.ITable` (or a plain DataFrame, coerced automatically). If
the user doesn't need to *do* anything with the table besides read it,
prefer plain `render.data_frame` instead — reach for itables when you need
its specific feature catalog: global search, CSV/Excel export, faceted
SearchPanes filters.

## Quick start

```python
from itables.widget import ITable
from shinywidgets import render_itables

@render_itables
def table():
    return ITable(df, select=True)
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `selected()` | Selected row positions (`df.iloc[table.selected()]`) | `[]` |

Row positions are already in your original data's order and survive
sort/search. `selected_rows()` is itables' convention elsewhere in the
roster for "rows of `df`," but this renderer's accessor is named
`selected()` — read `table.selected()`, not `table.selected_rows()`.

## Updating in place

Set `table.widget.selected_rows = [...]` to change the selection from
Python without re-rendering (note: `.update()` drops some display options,
so a structural change still needs a re-render).

## Gotchas

- Needs `select=True` (or an equivalent itables option) on the `ITable` to
  make rows selectable at all.
- The whole frame ships client-side; itables downsamples past a payload
  size (`maxBytes`) rather than scaling indefinitely — see the itables
  guide for the exact threshold if you're near it.
- itables is one of two widgets (with bqplot) whose own CSS variables
  shinywidgets patches onto Bootstrap's, so it follows
  `ui.input_dark_mode()` automatically — most other table/chart widgets
  don't.

**More:** <https://shinywidgets.org/widgets/itables/>
