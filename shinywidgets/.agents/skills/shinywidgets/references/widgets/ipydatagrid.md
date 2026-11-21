# ipydatagrid (`render_ipydatagrid`)

## Overview

`pip install 'shinywidgets[ipydatagrid]'`. A canvas-rendered,
spreadsheet-style data grid with rectangular cell-block selection, in-cell
bars/heatmaps, and editable cells — the only widget in the roster with
real cell-block (not just row) selection. Accepts a `pandas.DataFrame`
(coerced to a `DataGrid`) or a `DataGrid` directly — pass a `DataGrid` to
set `selection_mode`, `editable`, or cell renderers.

## Quick start

```python
import pandas as pd
from ipydatagrid import DataGrid
from shinywidgets import render_ipydatagrid

df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})


@render_ipydatagrid
def grid():
    return DataGrid(df, selection_mode="row")
```

A plain DataFrame return uses ipydatagrid's default `selection_mode="none"`
— nothing is selectable until you return `DataGrid(df, selection_mode="row")`
(or `"cell"`/`"column"`).

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `selected()` | Selection rectangles `[{"r1","r2","c1","c2"}, ...]`, in *visible* (post-sort/filter) coordinates | `[]` |
| `clicked_cell()` | Dict with `row` (visible), `primary_key_row` (data), `column`, `cell_value` | `None` |
| `edited_cell()` | Dict with `row` (data), `column`, `value` | `None` (requires `editable=True`) |
| `visible_data()` | The grid's rows as currently displayed, as a DataFrame | the whole frame |

`selected()` is debounced 250ms by default (dragging reports continuously)
and clears on sort. Map rectangles to data rows with
`.widget.get_visible_data()` or `.visible_data()`. **Replacing data in
place (`grid.data = df`) does not clear the selection** — ipydatagrid keeps
it, so rectangles then refer to positions in the old frame; clear it
yourself (`grid.selections = []`) when replacing data, and key selected
rows by the frame's index rather than position.

## Updating in place

`.transform()`, `.set_cell_value*()`, or assigning `.selections` directly.
`DataGrid.select()`/`.clear_selection()` and cell edits made via the
widget's own methods modify state in place without triggering
`reactive_read()` — assign a new list to `.widget.selections` instead, and
use `.widget.on_cell_change()` to react to edits:

```python
from shiny import reactive


@reactive.effect
def _clear_selection():
    grid.widget.selections = []
```

## Gotchas

- Cell renderers and scales are widgets themselves — create them inside the
  render function, not at import time.
- **ipydatagrid freezes its light/dark palette when a grid view is
  created** — toggling `ui.input_dark_mode()` only re-themes grids rendered
  *after* the toggle; re-render the output to re-theme an existing one.
- A continuously-streaming `selected()` with no rate limit can stall the
  browser on a large drag if a downstream reader rebuilds something
  expensive on every tick — update a companion view in place instead.

**More:** <https://shinywidgets.org/widgets/ipydatagrid/>
