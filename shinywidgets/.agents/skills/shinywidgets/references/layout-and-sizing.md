# Layout and sizing

## Overview

Every `@render_*` decorator runs the widget through one shared layout pass
(`set_layout_defaults()`) before it reaches the browser: with no explicit
height, a widget fills its container (a card, a sidebar, a column); any
explicit height opts it out to a fixed size instead. There's no
shinywidgets-wide dark-mode feature — `ui.input_dark_mode()` is a plain
Shiny input, and each widget decides for itself whether it listens to the
page's theme.

## Fill is the default

```python
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007")

ui.page_opts(title="Fill vs. fixed height", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Fills the card (no explicit height)")

    @render_plotly
    def fills():
        return px.scatter(df, x="gdpPercap", y="lifeExp", log_x=True)


with ui.card():
    ui.card_header('render_plotly(height="220px")')

    @render_plotly(height="220px")
    def fixed():
        return px.scatter(df, x="gdpPercap", y="lifeExp", log_x=True)
```

Three equivalent ways to give a widget an explicit height, any of which
flips the per-render `fill` flag to `False`:

1. The decorator's or `output_widget()`'s own `height=` — sizes the output
   container.
2. The widget's own constructor height, when the library has one
   (`Scatter(height=300)`, `k3d.plot(height=250)`, ...).
3. A plain `ipywidgets.Layout(height=...)` assigned to `.layout`.

**A library's own default height often can't be told apart from a real
one.** lonboard (500px), maplibre/rerun (400/640px), k3d (512px), jscatter
(240px), and several others always set a concrete height trait, so a height
you ask for that happens to equal the library's default is treated as
"unset" and the widget still fills. If you want a genuinely fixed size at
that exact number, ask for a slightly different one (e.g. `height=241`
instead of jscatter's default `240`). The widget's own reference names its
specific default.

## `widget.layout.height` has no effect after render

`set_layout_defaults()` reads `.layout.height` exactly once, at render time,
to decide the `fill` flag for that render; filling itself is plain CSS
applied once the payload reaches the browser. Setting `.layout.height` later
from a `@reactive.effect` updates the trait (anything reading it with
`reactive_read()` sees the new value) but doesn't resize anything — there's
no later CSS pass that reads it again. To actually resize a widget in
place, resize its *container*; to pick up a new height as a real opt-out,
re-render.

## `full_screen=True`

`ui.card(full_screen=True)` adds an expand icon; the widget inside resizes
to match, exactly like any other container resize (a window resize, a
sidebar collapse). This isn't shinywidgets-specific — bslib fires a resize
event the widget's own resize handling already picks up. A few widgets have
a wrinkle worth knowing (e.g. ipycytoscape doesn't re-run its own graph
layout on resize, so part of the graph can end up outside the visible
area) — see that widget's reference.

## Dark mode and theming

`ui.input_dark_mode()` flips `data-bs-theme` on `<html>`, cascading
Bootstrap's CSS variables to anything that reads them. shinywidgets patches
exactly bqplot and itables's own CSS variables onto those Bootstrap
variables, plus the chrome (not the tile imagery) of ipyleaflet maps. Every
other widget draws its own colors with no connection to the page theme —
plotly, altair, bokeh, matplotlib, maplibre, lonboard, and reactable do
**not** follow `input_dark_mode()` automatically (reactable is actually
worse in dark mode: its background stays hard-coded white while its text
switches to Bootstrap's light-gray dark-mode color, which is lower contrast
than either theme alone — [#460](https://github.com/posit-dev/py-shinywidgets/issues/460)).

To make a non-following widget match the toggle anyway, read `input.<id>()`
in a `@reactive.effect` and re-theme the figure **in place** (update
`.widget`, don't re-render, or you lose zoom/selection):

```python
from shiny import reactive
from shiny.express import input, ui

ui.input_dark_mode(id="mode")


@reactive.effect
def _sync_theme():
    dark = input.mode() == "dark"
    plot.widget.update_layout(template="plotly_dark" if dark else "plotly_white")
```

## Common mistakes

- Choosing a fixed height that happens to equal a GPU/WebGL widget's own
  default (lonboard 500px, k3d 512px, ...) and being confused that it still
  fills — ask for a slightly different number.
- Setting `.widget.layout.height` from an effect expecting it to resize an
  already-filling widget — it only affects the next render's fill decision.
- Assuming a widget follows `ui.input_dark_mode()` because the surrounding
  card goes dark — most widgets draw their own colors independent of the
  page theme; only bqplot, itables, and ipyleaflet's chrome follow
  automatically.

**More:** <https://shinywidgets.org/guide/layout-and-theming/>
