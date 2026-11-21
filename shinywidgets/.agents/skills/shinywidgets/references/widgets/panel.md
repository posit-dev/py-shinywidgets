# Panel (`render_panel`)

## Overview

`pip install 'shinywidgets[panel]'`. Drop any Panel component — a pane,
widget, layout, `pn.viewable.Viewer`, DataFrame, or figure — into a Shiny
app, rendered through bokeh. Panel callbacks (`pn.bind()`, `.param.watch()`,
`on_click()`) run in the Shiny server, with no separate Panel server
needed. Create Panel objects per session (inside the render function), not
at the top level of a Shiny Core app.

## Quick start

```python
import panel as pn
from shinywidgets import render_panel

pn.extension()


@render_panel
def hello():
    return pn.pane.Markdown("# Hello, panel!")
```

Call `pn.extension()` with every extension you use (e.g.
`pn.extension("tabulator")`) at the top of the app — components that first
appear after the initial render (inside `pn.bind()`) render blank
otherwise. Set `sizing_mode="stretch_both"` on the panel object to fill the
output. Panel templates are full pages and can't be rendered in an
output — use Shiny's own page layouts instead.

## Accessors

Panel parameters aren't widget traits, so `reactive_read()` can't see them.

| Accessor | Returns | Before first interaction |
|---|---|---|
| `param(name)` | The rendered object's `name` parameter, read reactively | seeded with the parameter's value at render |

```python
@render_panel
def slider():
    return pn.widgets.IntSlider(value=5, start=0, end=10)


@render.text
def value():
    return str(slider.param("value"))
```

`param()` raises if `.value` isn't a `param.Parameterized` or has no `name`
parameter — return a pane/widget explicitly rather than a raw DataFrame or
string if you need a parameter interface. To limit how often a dragged
slider re-runs readers, read Panel's throttled variant instead
(`slider.param("value_throttled")`). For anything more involved,
`.param.watch()` on the object works too and may set `reactive.value`s.

## Updating in place

Modify `.value` in place rather than re-rendering:

```python
@reactive.effect
def _update_table():
    table.value.value = new_df
```

## Gotchas

- A component that appears only after `pn.bind()` runs renders blank unless
  its extension was already declared with `pn.extension(...)` up front.
- `.value` is the return value exactly as returned — to get a parameter
  interface, return a pane/widget, not a raw value.

**More:** <https://shinywidgets.org/widgets/panel/>
