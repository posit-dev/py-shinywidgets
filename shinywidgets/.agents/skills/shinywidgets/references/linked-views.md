# Linking widgets

## Overview

Most real dashboards need two or three views of the same data talking to
each other: lasso a cluster in a scatter plot and see those rows in a
table; click a map feature and see its detail; pan a map and watch a chart
summarize only what's on screen. Every pattern below is built the same way
— one accessor read feeding another output or effect through Shiny's
reactive graph — never a hidden input or custom JS message bus.

## Pattern picker

| Goal | Pattern | Typical pairing |
|---|---|---|
| See exactly which records are selected | Selection → table | A chart's `selected_rows(df)` → `itables`/`render.data_frame` |
| Show everything about one clicked thing | Click → detail card | A map/graph/chart's click accessor → a `@render.ui` detail card |
| Summarize only what's on screen | Viewport → summary | A map's `bounds()`/`view_state()` → a filtered `plotly`/`matplotlib` chart |
| Drive a chart/map from a row click, in place | Table → plot/map | `itables`'s `selected_rows()` → write the target's `.widget` trait from an effect (not a re-render, or you lose zoom/selection) |
| Keep two views of the same selection in sync | Two-way linking | See "Avoiding loops" below |
| Let several charts narrow down together | Crossfilter | In-widget (altair `transform_filter`, mosaic `filterBy`) vs. through Shiny (read one widget's selection, write another's) |
| Keep a brush fluid over millions of rows | Brushing large data | Push summaries (rasterized image, aggregate query), never raw points — see below |
| Feed a stat line, a table, and a chart from one gesture | One selection, many views | One accessor read → a shared `@reactive.calc` → every output reads the calc |

## Avoiding loops

Two widgets mirroring each other's selection have the same risk as an
effect that reads-and-writes its own state (see `updating-in-place.md`'s
`isolate()` trap) — except the cycle runs *between* two widgets instead of
within one effect. Two techniques:

**Direct trait mirroring with an equality guard**, when both widgets expose
a compatible, Python-settable selection trait:

```python
import numpy as np
from shiny import reactive


def link(source, target):
    @reactive.effect
    def _():
        selection = source.selected()
        with reactive.isolate():
            if not np.array_equal(selection, target.widget.selection):
                target.widget.selection = selection


link(plot_a, plot_b)
link(plot_b, plot_a)
```

The guard is the whole safety mechanism: A sets B (different, so it
writes); B's effect reads the new value, finds it equal to what's already
there, and does nothing — breaking the cycle instead of looping forever.

**A shared broker value**, when the two widgets don't share a compatible
trait (a map pick and a plot click are different *kinds* of event): route
both through one `reactive.value` instead of wiring the widgets directly to
each other. Each widget's own effect only ever writes to the broker
(guarded the same way); separate effects fan the broker out to each
widget's in-place highlight. Neither widget's effect reads the *other*
widget's accessor, so there's no cycle to break in the first place.

## Crossfilter: in-widget vs. through Shiny

Some libraries crossfilter *inside themselves* with no Shiny code at all —
altair's `transform_filter` against a shared selection, mosaic's
`filterBy`. Reach for Shiny-mediated crossfilter (read one widget's
selection accessor, write another's filter/highlight) when the views are
different libraries that have no shared in-widget mechanism, or when a
Shiny-side aggregate (a summary table, a derived stat) needs to see the
same filter.

## Brushing large data: push summaries, not points

Lassoing a scatter plot of millions of raw points (e.g. plotly's
`Scattergl`) is the anti-pattern — the selection payload itself grows with
the number of points caught, and the browser has to render every mark in
the first place. Push a **summary** instead: a server-side rasterized image
that re-aggregates per zoom (`datashader`/`holoviews`), or a widget whose
own query engine re-aggregates for you (`mosaic`, `quak`). Both keep the
payload roughly flat regardless of how many underlying rows the brush
covers.

## Common mistakes

- Re-rendering the target widget from a row click instead of updating
  `.widget` in place — resets the zoom/selection the user already made.
- Linking two widgets' selections without an equality guard or a broker —
  causes either an infinite loop or (with array equality that always
  differs) double work on every gesture.
- Lassoing raw points at scale instead of pushing a pre-aggregated summary.

**More:** <https://shinywidgets.org/guide/linked-views/>
