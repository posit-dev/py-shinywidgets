# Any widget (render_widget, anywidget)

## Overview

`render_widget` renders *any* `ipywidgets.Widget` subclass — a plain
control, a third-party widget with no dedicated renderer yet, or one you
wrote yourself with [anywidget](https://anywidget.dev/) — with no
library-specific coercion and no accessors of its own. Don't reach for it
when a dedicated `render_<library>` exists: the dedicated renderer adds
layout defaults tuned to that widget and usually a handful of typed,
rate-limited accessors. Use `render_widget` when there's no dedicated
decorator, or when you're building the widget yourself.

```python
from ipywidgets import IntSlider
from shinywidgets import render_widget

@render_widget
def slider():
    return IntSlider(value=7, min=0, max=10, description="Threshold:")
```

It applies the same `as_widget()` coercion and generic fill-sizing every
renderer shares, and gives you `.widget` (mutate in place) and
`.read("trait")` (a documented shortcut for `reactive_read(.widget,
"trait")`).

## Writing a custom widget with anywidget

anywidget is one Python class, a JS `_esm` string implementing
`render({ model, el })`, and optionally `_css` — no build step. Every trait
declared with `.tag(sync=True)` syncs both directions automatically:

```python
import anywidget
import traitlets

class Sparkline(anywidget.AnyWidget):
    _esm = """
    function render({ model, el }) {
      // model.get("values") / model.on("change:values", draw) -- Python -> JS
      // model.set("clicked_index", i); model.save_changes(); -- JS -> Python
    }
    export default { render };
    """
    values = traitlets.List(traitlets.Float()).tag(sync=True)
    clicked_index = traitlets.Int(allow_none=True, default_value=None).tag(sync=True)
```

```python
from shiny import reactive
from shinywidgets import render_widget

@render_widget
def spark():
    return Sparkline(values=[1.0, 3.0, 2.0])

@reactive.effect
def _update():
    spark.widget.values = [2.0, 4.0, 1.0]  # pushed in place, no new comm
```

**JS → Python requires `model.save_changes()`** after `model.set(...)` —
without it, the browser's local trait copy changes but Python never sees it.
Once called, `spark.read("clicked_index")` behaves like any synced trait.

**Custom messages** (not state worth remembering — "the user asked to
reset"): `model.send()` (JS → Python, read with `widget.on_msg()`) and
`widget.send()` (Python → JS, read with `model.on("msg:custom", ...)`). A
`widget.send()` called before the widget's comm opens is queued and
delivered once it does, not dropped.

## Reacting to user interaction

No named accessors exist for `render_widget` itself. Read any trait
reactively with `.read("trait")` (an output) or `reactive_read(obj, "trait")`
(a nested widget the output doesn't wrap directly — a child widget a parent
owns). To find a trait worth reading, skim the widget class's
`trait_names()` for anything user-facing, then confirm with `reactive_read()`
that it actually updates from the browser — some upstream-internal traits
don't sync reliably.

## Updating the widget from Python

Push a new value onto an existing trait (`spark.widget.values = [...]`) —
the browser redraws in place, with no new comm and no re-sent JS bundle.
The same pattern works for any built-in widget in the roster; it's the
mechanism every dedicated renderer uses internally.

## Layout and sizing

Plain ipywidgets **controls** (sliders, dropdowns, checkboxes — anything in
`@jupyter-widgets/controls`) never fill their container, regardless of
layout; they render at their natural size. A `<canvas>`-based custom widget
needs to handle its own sizing — the fill mechanism is `flex: 1 1 auto` on
the widget's direct DOM child, and a canvas's `width`/`height`
*attributes* (its drawing-buffer resolution) don't count as a CSS size, so
an unstyled canvas gets stretched and blurred. Pin `style.width`/
`style.height` to match the buffer size, or add a `ResizeObserver` that
resizes the buffer and redraws when the container's size genuinely should
scale.

## Gotchas

- **`ipydeck`'s accessor properties need a literal `@@=` prefix**
  (`get_position="@@=position"`) — the plain form (pydeck's own convention)
  silently renders nothing.
- **`with out: print(...)` inside an `ipywidgets.Output()` renders
  nothing** — there's no real IPython kernel to route it; use
  `out.append_stdout(...)` / `out.append_display_data(...)` instead.
- **Name your output carefully.** `@render_widget def map(): ...` shadows
  the Python builtin `map()` for the rest of that module.

**More:** <https://shinywidgets.org/guide/any-widget/>
