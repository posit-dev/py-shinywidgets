# lonboard (`render_lonboard`)

## Overview

`pip install 'shinywidgets[lonboard]'`. Render tens or hundreds of
thousands of GPU-accelerated map points, with pan/zoom/click/box-select
wired back to Python — the scale answer among the map widgets in this
roster. Accepts a `lonboard.Map`, a lonboard layer (or list of layers), or
any data `lonboard.viz()` accepts (a GeoPandas `GeoDataFrame`, a
GeoArrow-compatible Arrow table).

## Quick start

```python
import geopandas as gpd
from shapely.geometry import Point
from shinywidgets import render_lonboard

cities = gpd.GeoDataFrame(
    {"city": ["SF", "NYC"]},
    geometry=[Point(-122.42, 37.77), Point(-74.01, 40.71)],
    crs="EPSG:4326",
)


@render_lonboard
def map():
    return cities
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `view_state()` | `MapViewState`/`GlobeViewState` (`.longitude`, `.latitude`, `.zoom`, `.pitch`, `.bearing`) | never `None` once rendered |
| `selected()` | Positional index of the most recently picked row, across layers | `None` |
| `selected_rows(df=None)` | The picked row of `df` (or a frame rebuilt from the pickable layer) | empty frame |
| `selected_bounds()` | `(minx, miny, maxx, maxy)` from the Select BBox control | `None` |
| `clicked()` | `(lng, lat)` of the last click — note the order; ipyleaflet is `[lat, lng]` | `None` |

`view_state()` is debounced 250ms by default. `selected()` is the most
recent pick *across* all pickable layers — it doesn't say which layer; with
several pickable layers, read each layer's own `selected_index` directly
(`reactive_read(layer, "selected_index")`), and `selected_rows()` raises
without an explicit `df` in that case. Picking the same row twice doesn't
re-fire; clicking empty space doesn't clear a pick. A layer only reports
when `pickable=True` (the default). Indices/positions are into the layer's
data — a retained value can point at a different row after an in-place
`layer.table = ...` replacement; carry an ID column if rows can change.

## Updating in place

Set a layer's trait to restyle (`layer.<trait> = ...`), or move the camera
with `map.widget.fly_to(...)`:

```python
from shiny import reactive


@reactive.effect
def _recolor():
    map.widget.layers[0].get_fill_color = new_colors
```

## Gotchas

- **Per-point colors need a numpy `uint8` array** (e.g. from
  `apply_continuous_cmap`), not a list of RGB tuples — a list is read as one
  color and raises a confusing `TraitError`.
- **Upstream bug: `GlobeView` permanently breaks `view_state()` sync** —
  the browser sends pitch/bearing that `GlobeViewState` has no fields for,
  and the sync throws silently and never recovers. Stick to the default
  `MapView` if you need `view_state()`.
- **Rendering a lonboard map alongside a maplibre map on the same page
  crashes lonboard's view** (`deck.gl - multiple versions detected`) — keep
  them on separate pages.
- `lonboard.viz()` draws no basemap at all unless passed one explicitly.

**More:** <https://shinywidgets.org/widgets/lonboard/>
