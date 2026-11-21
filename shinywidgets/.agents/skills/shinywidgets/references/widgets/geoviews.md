# GeoViews (`render_holoviews`)

## Overview

`pip install 'shinywidgets[holoviews]' geoviews "cartopy<0.26"`. There is
no dedicated `render_geoviews` — GeoViews maps render through the same
[`@render_holoviews`](holoviews.md) decorator as plain
HoloViews/hvPlot. Cartopy-projected, tile-backed Bokeh maps from
HoloViews/hvPlot elements. The `cartopy<0.26` pin matters: geoviews
1.15/1.16 raise `KeyError: 'lon_0'` on cartopy 0.26 (fixed upstream,
unreleased as of writing).

## Quick start

```python
import geoviews as gv
import holoviews as hv
from shinywidgets import render_holoviews

hv.extension("bokeh")


@render_holoviews
def map():
    points = gv.Points(carshare, kdims=["centroid_lon", "centroid_lat"]).opts(
        color="car_hours",
        cmap="viridis",
        size=8,
        tools=["hover"],
    )
    return (gv.tile_sources.OSM * points).opts(responsive=True)
```

`gv.tile_sources.OSM * points` is the whole recipe: a tile layer overlaid
(`*`) with a projected element. `kdims` are the point's coordinate columns
(GeoViews assumes `PlateCarree`/plain lon-lat unless you pass `crs=`).
**Avoid `CartoLight`/`CartoDark`**: they now require an API key and render
a watermark instead — use an Esri preset or `OSM`.

## Accessors

None directly — see `holoviews.md`'s general stream-subscriber pattern
(`Tap`, `BoundsXY`, `RangeXY`). Stream values come back in the element's
native coordinates (lon/lat), not the tile layer's Web Mercator, even
though the tiles themselves are Mercator — no conversion needed when
reading stream values.

## Updating in place

Same mechanism as `holoviews.md`: drive a `DynamicMap` with
`hv.streams.Pipe` to filter/update data without losing pan/zoom. Attach
streams to the `DynamicMap` object itself
(`hv.streams.Tap(source=dmap)`), not to the element a callback returns —
a stream created inside the callback is a fresh, disconnected object every
call, and the subscriber is simply never invoked (no error).

## Gotchas

- **A non-Mercator `projection=` drops any tile layer silently** (no
  error) — tiles are Web-Mercator-only raster images with no server-side
  reprojection path.
- **`.opts()` on `gv.tile_sources.*`/`gv.feature.*` mutates the shared
  module-level object in place** — style with `.opts(..., clone=True)` or
  one session's styling leaks into every other session reusing the same
  object.
- **`gv.feature.*` (coastline, borders, ocean, land) downloads Natural
  Earth shapefiles synchronously on first use**, inside the render call —
  pre-warm Cartopy's data cache on an offline server.
- **An empty element (e.g. a `req()`-guarded selection filtering
  everything) collapses the map's extent** to a near-zero-degree box,
  flooding the tile server with deepest-zoom requests — guard inputs that
  could produce an empty frame.
- Plain (non-rasterized) `gv.Points`/`gv.Polygons` render fine into the low
  thousands; past that, use `rasterize=True` (see `datashader.md`) or
  switch to `lonboard.md` if individual points need to stay pickable.

**More:** <https://shinywidgets.org/widgets/geoviews/>
