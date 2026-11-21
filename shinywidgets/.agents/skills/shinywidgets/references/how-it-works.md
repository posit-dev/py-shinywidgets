# How shinywidgets fits Shiny

## Overview

shinywidgets renders [ipywidgets](https://ipywidgets.readthedocs.io) (plotly
figures, altair charts, maps, tables, ...) as Shiny outputs. A render
function decorated with `@render_widget` (generic) or a library-specific
`@render_<library>` (e.g. `@render_plotly`) is an **output**: Shiny calls it
and displays whatever `Widget` it returns, where the function appears
(Express) or wherever `output_widget("id")` is placed (Core). The same
decorator also adds **accessors** — methods that read back what the user did
in the browser (a click, a selection, a zoom) as ordinary reactive values —
and a `.widget` attribute for updating the rendered widget **in place**
instead of re-running the render function. Don't read `input.*()` inside a
render function just to force a rebuild on every change; read it in a
`@reactive.effect` that mutates `.widget` instead (see
`updating-in-place.md`).

## Render a widget (Express)

```python
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007")

ui.page_opts(title="Gapminder 2007", fillable=True)


@render_plotly
def plot():
    return px.scatter(df, x="gdpPercap", y="lifeExp", color="continent", log_x=True)
```

In Shiny Express, the decorated function displays where it's defined — no
separate UI call needed. In Shiny Core, pair it with `output_widget("plot")`
in `app_ui`, and put the decorated function inside `server()`:

```python
from shiny import App, Inputs, Outputs, Session, ui
from shinywidgets import output_widget, render_plotly

app_ui = ui.page_fillable(output_widget("plot"))


def server(input: Inputs, output: Outputs, session: Session):
    @render_plotly
    def plot():
        return px.scatter(df, x="gdpPercap", y="lifeExp", log_x=True)


app = App(app_ui, server)
```

shinywidgets doesn't know or care which mode built the app around it: the
renderer, `.widget`, and every accessor behave identically either way, and
again inside a Shiny module (`@module.ui`/`@module.server`, or Express's
`@module`) — each module instance gets its own renderer object with its own
accessor state, completely independent of other instances of the same
module.

## Reactive, not event-driven

Responding to a widget interaction isn't a callback you write per event.
What the user did (a lasso selection, say) is captured as a reactive value;
any output or effect that calls the accessor re-runs when it changes, the
way a spreadsheet formula updates when a cell it reads changes:

```python
from shiny import req
from shiny.express import render


@render_plotly(listen_to=["selected"])
def plot():
    fig = px.scatter(df, x="gdpPercap", y="lifeExp", custom_data=[df.index])
    return fig.update_layout(dragmode="lasso")


@render.data_frame
def selected_countries():
    rows = plot.selected_rows(df)
    req(not rows.empty)
    return rows[["country", "lifeExp"]]
```

Adding another view that depends on the same selection means writing one
more function that calls the same accessor — nothing about `plot` changes.
`reacting-to-widgets.md` covers what every accessor has in common (what it
returns before the first interaction, rate limiting, `listen_to`).

## Re-render vs. in-place update

Rebuilding a widget (re-running its render function because it read a
changed `input.*()`) sends the whole widget back to the browser and resets
the user's zoom and selection — for a big chart that's slow, and it resends
the widget's JS too. Writing to `.widget` from a `@reactive.effect` instead
changes only what's different, keeps the zoom and selection, and is far
smaller on the wire (recoloring a plotly chart in place: ~36 KB; rebuilding
it: ~5.5 MB, measured in `performance.md`). Prefer in-place updates whenever
a `@reactive.effect` can express the change; reach for a full re-render only
when the change is structural (a different plot type, a different number of
traces) and `updating-in-place.md` doesn't show a matching call. See that
reference for the mechanism and the `reactive.isolate()` rule that keeps a
writing effect from re-triggering itself.

## Common mistakes

- Reading `input.*()` inside the render function to react to it, instead of
  writing to `.widget` from a `@reactive.effect` — this rebuilds the whole
  widget and loses zoom/selection on every change.
- Assuming Core needs different decorators than Express — it doesn't; only
  `output_widget()` placement and the `app_ui`/`server()` scaffolding differ.
- Worrying that two instances of the same module share widget/accessor
  state — they don't; each module instance's renderer is independent.

**More:** <https://shinywidgets.org/guide/why/>,
<https://shinywidgets.org/guide/first-app/>,
<https://shinywidgets.org/guide/core-and-modules/>
