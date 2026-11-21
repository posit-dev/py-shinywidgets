# HoloViews (`render_holoviews`)

## Overview

`pip install 'shinywidgets[holoviews]'`. Declarative, composable Bokeh
plots — crossfilter several views at once with `hv.link_selections`.
Accepts a holoviews/hvPlot/geoviews object (rendered through panel) or the
underlying `jupyter_bokeh.BokehModel`. If you call `.opts()` without
importing hvplot, call `hv.extension("bokeh")` first. Also renders
[geoviews](geoviews.md) objects and
[datashader](datashader.md)-rasterized plots — those have their own
references for library-specific gotchas.

## Quick start

```python
import holoviews as hv
from shinywidgets import render_holoviews


@render_holoviews
def curve():
    return hv.Curve([1, 2, 3])
```

HoloViews/hvPlot plots have a fixed size by default and get clipped by a
smaller container. To fill the output, pass `responsive=True`
(`df.hvplot.line(..., responsive=True)` or `.opts(responsive=True)`); if
you also give the output a fixed `height`, set `fillable=True` too, or a
responsive plot collapses to a thin strip.

## Accessors

No named accessors — HoloViews' own Python-side interactivity (widgets for
a `HoloMap`/`DynamicMap`, streams like `Selection1D`/`BoundsXY`,
`hv.link_selections`) works without a Bokeh server. React to it in Shiny by
setting a `reactive.value` from a stream subscriber or a `.param.watch()`
callback:

```python
from shiny import reactive

selection = reactive.value(None)
links = hv.link_selections.instance()
links.param.watch(lambda e: selection.set(e.new), "selection_expr")
```

Create streams and `link_selections` instances **per session** (inside the
render function, or anywhere in an Express app) — never at Shiny Core's
module level, where every visitor would share them and see each other's
selections.

## Updating in place

Drive a `DynamicMap` with a stream from a `@reactive.effect` —
`stream.event(...)` or `pipe.send(...)` — instead of re-rendering.

## Gotchas

- **Build the plot inside the render function, never at module level** — a
  module-level `DynamicMap` is shared by every session, so one visitor's
  zoom repaints everyone's plot.
- **Linked streams run their callbacks outside Shiny's reactive cycle**
  with shiny < 1.9 — updates they trigger only reach the browser after the
  next unrelated input.
- **`.opts()` styles shared objects in place** (`gv.tile_sources.OSM`,
  `gv.feature.coastline`) — use `.opts(..., clone=True)` on them, or one
  session's styling shows up in every session.
- A composite `hv.link_selections` `Layout` defaults to the Pan tool, not
  box-select — set `.opts(active_tools=["box_select"])` on each element.

**More:** <https://shinywidgets.org/widgets/holoviews/>
