# Reacting to widgets

## Overview

A renderer's **accessors** turn what the user did in the browser into an
ordinary Shiny input: `plot.clicked()` called in a reactive context behaves
exactly like `input.my_slider()`. Don't poll a widget's state or hand-wire a
JS event to a hidden input — read the matching accessor instead. Every
accessor attaches the moment its output renders (not on first read) and
records the interaction whether or not anything has read it yet, so it's
always safe to read later, on demand.

## Before the first interaction

Reading an accessor before its output has ever rendered cancels silently
(like `req(False)`). After that, each accessor settles into one of four
states, which never changes for that accessor:

| State | Meaning | Example |
|---|---|---|
| cancels | browser hasn't reported it yet | k3d's `camera()` before auto-fit |
| `None` | nothing has happened yet | ipyleaflet's `clicked()` |
| `[]` / `{}` | same as `None`, but naturally a collection | bokeh's `selected()` |
| seeded value | never "empty" in a special sense | altair's `selected()` |

```python
from shiny import req
from shiny.express import render


@render.code
def clicked_out():
    pt = map.clicked()
    return "None (click the map)" if pt is None else str(pt["coordinates"])
```

`req(map.clicked())` is the idiom for waiting on a `None`-until-interaction
accessor. Never leave a bare `req(x)` as a top-level statement inside
`@render.express` — it renders the value; assign it first: `clicked =
req(map.clicked())`. Each widget reference's accessor table says which state
applies.

## Across re-renders

A re-render builds a brand-new widget. **User-interaction state** (clicks,
taps, gestural selections) is *kept* — the accessor keeps reporting the last
interaction until the user interacts with the new widget. **Inherent widget
state** (viewport, zoom, camera, axis limits) is *re-seeded* from the new
widget every render. Either way, readers only re-run when the value actually
changes. The catch: a kept payload can describe the *previous* render's
widget — if the re-render swapped in new data, a retained positional field
(a point index, a row position) can silently point at something else. Key
off something stable (an ID column, `customdata`) instead of a position
whenever the underlying data can change across a render, and guard any
lookup by that ID (`.get()` with a default, filter + check `.empty`) rather
than letting an unresolved ID crash the reactive flush.

## Read on demand

Because an accessor records from render time, not from its first read, a
gesture made before any code reads it is never lost. This makes it safe to
read a selection from a button handler, a `@reactive.event`-gated output, a
download handler, or an LLM tool call — all of these can read
`plot.selected_rows()` long after the user interacted, with nothing missed
in between. One qualifier: a few accessors are **opt-in** because their
payload can grow without bound (plotly's `selected()`, kepler.gl's
`config()`) — declare them with `listen_to=["selected"]` on the decorator;
reading an undeclared opt-in accessor raises, pointing at `listen_to`.

## Re-firing and clearing

Most accessors **dedup**: a value equal to the last one published doesn't
invalidate readers (clicking the same point twice fires once). A few are
**pulses** (e.g. plotly's `double_clicked()`) — they re-fire readers even on
an unchanged value, because the gesture itself is the meaningful thing, not
the value.

## Rate limiting

A gesture can report as a burst of many trait changes (selecting 1,000
ipycytoscape nodes sends 1,000 updates), queuing up re-runs that make the app
look frozen. In order of preference:

1. Read an accessor that already collects the burst (`selected_nodes()`
   instead of looping over every node's own `selected` trait).
2. Rate-limit with the renderer's `rate_policy`/`rate_delay` kwargs, e.g.
   `@render_plotly(rate_delay=0)` — these only affect accessors that declare
   a default rate policy (almost always `"debounce"`, 250ms) in the first
   place, plus `reactive_read()` on `.widget` directly; an accessor with no
   declared default ignores them and always publishes immediately.
3. Debounce the expensive step itself: `@reactive.debounce(0.5)` directly
   below `@reactive.calc` — only the calc's readers wait.

## Rows of your data

Most selection-reporting widgets report their *own* coordinate space (a
point index, a row position), not a row of your data frame.
`selected_rows()` (plotly, altair, bokeh, itables, reactable, jscatter,
bqplot, lonboard) closes that gap:

```python
import plotly.express as px
from shinywidgets import render_plotly

df = px.data.tips().reset_index(drop=True)


@render_plotly(listen_to=["selected"])
def plot():
    fig = px.scatter(df, x="total_bill", y="tip", custom_data=[df.index])
    return fig.update_layout(dragmode="select")


# elsewhere: plot.selected_rows(df) -- matched back to df by df.index
```

`custom_data=[df.index]` is plotly's contract — each point carries its row's
index label, matched by label (not position), so it survives a filtered or
re-sorted `df`. Other libraries have their own mechanism: altair replays its
Vega-Lite selection test against `df`; bokeh reads its plot's own
`ColumnDataSource`; itables/reactable return row positions already in your
original data's order. See the relevant widget reference for the exact
signature.

## `.read()` and `reactive_read()`

Reach for these in order, after the accessor methods:

1. **`output.read("name")`** — reads an accessor by name (`plot.read("selected")`
   is exactly `plot.selected()`); falls through to a bare synced trait when
   `"name"` isn't an accessor. An unknown name raises `AttributeError` with
   a "did you mean" hint.
2. **`reactive_read(obj, "trait")`** — for widgets that *aren't* the output
   itself: a child widget a parent owns (an ipyleaflet layer, an
   ipycytoscape `Node`), or any widget built outside a renderer.

## Common mistakes

- Treating `clicked()`/`selected()` as events you must read immediately —
  they're safe to read on demand, long after the gesture.
- Trusting a kept accessor's positional field after a re-render changed the
  underlying data — key off a stable ID instead.
- Reading an opt-in accessor (plotly's `selected()`, etc.) without
  `listen_to=[...]` on the decorator.
- Expecting `rate_delay` to slow down an accessor with no declared default
  rate policy — it's a no-op for those.

**More:** <https://shinywidgets.org/guide/reacting-to-widgets/>
