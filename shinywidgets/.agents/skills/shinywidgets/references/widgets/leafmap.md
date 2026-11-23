# leafmap (`render_leafmap`)

## Overview

`pip install 'shinywidgets[leafmap]'`. One high-level API for basemaps,
vector/raster layers, legends, and split-panel maps across several
mapping engines. Return any widget-backed leafmap backend:

- `leafmap.leafmap.Map` (default; an `ipyleaflet.Map`) — leafmap's toolbar,
  basemap gallery, legends; start here.
- `leafmap.maplibregl.Map` (a maplibre `MapWidget`) — vector tiles, globe
  projection, deck.gl layers via `add_deck_layers()`.
- `leafmap.plotlymap.Map` (a Plotly `FigureWidget`) — requires
  `plotly>=5.12,<7` (included in the extra).
- `leafmap.kepler.Map` (a kepler.gl widget) — kepler.gl's layer/filter UI
  and time playback (its `config` trait nests kepler's own config, e.g.
  `config["config"]["mapState"]`).

leafmap's folium (`leafmap.foliumap.Map`) and pydeck (`leafmap.deck.Map`)
backends aren't ipywidgets — they raise a `TypeError` pointing to
alternatives.

## Quick start

```python
import leafmap.leafmap as leafmap
from shinywidgets import render_leafmap


@render_leafmap
def map():
    return leafmap.Map(center=(47.6, -122.3), zoom=10)
```

Maps fill their container (even in a non-filling `page_*()`) unless given
a height of their own (`leafmap.Map(height=400)` or
`Layout(height="300px")`) — leafmap's 600px default is treated as unset.

## Accessors

On the default (ipyleaflet) backend, the same five accessors as
[ipyleaflet](ipyleaflet.md): `bounds()`, `zoom()`, `center()`,
`clicked()`, `drawn_features()`. On the maplibre, plotly, and kepler
backends these **raise `TypeError`** — read those backends' state with
`.read(...)` instead (e.g. `.read("view_state")` for maplibre). For a trait
sharing an accessor's name, use `reactive_read()` on `.widget` directly
(`.read()` prefers the accessor).

## Updating in place

Mutate `.widget` directly — the same ipyleaflet-backed trait writes as
`ipyleaflet.md` on the default backend; each other backend's own
in-place API otherwise (e.g. maplibre's `set_paint_property`).

## Gotchas

- `.widget` is typed as an `ipyleaflet.Map` (the default backend); for
  another backend, `.widget` is that backend's widget at runtime — type
  checking is weaker there.
- The Plotly backend is already a `FigureWidget`, rendered directly;
  `.value` retains the original leafmap `Map` and its own methods.

**More:** <https://shinywidgets.org/widgets/leafmap/>

Written against `leafmap` 0.x.
