# reactable (`render_reactable`)

## Overview

`pip install 'shinywidgets[reactable]'`. A polished, R-reactable-style data
table — sorting, per-column/global filtering, pagination, row selection,
grouping/aggregation, expandable detail rows, custom cell renderers, and
themes, all computed client-side (interacting with the table never
round-trips to the server). Accepts a `reactable.Reactable` (coerced to its
widget) or a `reactable.widgets.ReactableWidget` directly. Richest
display/theming feature set of the table widgets in this roster.

## Quick start

```python
from reactable import Reactable
from reactable.data import cars_93
from shinywidgets import render_reactable

@render_reactable
def tbl():
    return Reactable(cars_93, filterable=True, searchable=True)
```

## Accessors

Each silently cancels (like `req(False)`) until the browser first reports
the table's state, shortly after it renders.

| Accessor | Returns | Notes |
|---|---|---|
| `selected()` | 0-based row positions in the table's *data* order | requires the table's `selection=` prop |
| `page()` | Current page, 0-based | add 1 to match the displayed page number |
| `sorted()` | `[{"id": column, "desc": bool}, ...]` | empty when unsorted |
| `filtered()` | `[{"id": column, "value": filter}, ...]` | debounced 250ms (updates per keystroke) |
| `search()` | Current global search string | `""` when empty; debounced 250ms |

`selected()`'s positions are into the *current* data — after a re-render or
a `.widget.props` data replacement, a retained position can point at a
different row until the table re-reports; include an ID column and resolve
against the currently-shown data if rows can change. Row *clicks* aren't
part of the reported state — forward them as an ordinary Shiny input with
reactable's own `on_click=JS(...)` prop instead.

## Updating in place

Send new data through `.widget.props` (preserves sort/filter/page/selection)
instead of re-rendering — `props` is itself a trait, so replace the whole
dict rather than mutating `.widget.props["data"]` in place, which never
syncs:

```python
from shiny import reactive

@reactive.effect
def _update_data():
    tbl.widget.props = {**tbl.widget.props, "data": new_df.to_dict(orient="records")}
```

Other props (e.g. `defaultPageSize`) update the same way.

## Gotchas

- Accessors address the table through its `element_id` prop;
  `render_reactable` defaults it to a unique value when unset — a
  user-provided `element_id` must stay unique per page.
- Setting reactable's own `height=` prop opts out of filling, the same as
  an explicit ipywidgets `Layout(height=...)`.
- **In dark mode, the table's background stays hard-coded white while its
  text switches to Bootstrap's light-gray dark-mode color** — lower
  contrast than either theme alone, not merely unchanged
  ([#460](https://github.com/posit-dev/py-shinywidgets/issues/460)).

**More:** <https://shinywidgets.org/widgets/reactable/>
