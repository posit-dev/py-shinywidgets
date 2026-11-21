# localtileserver (`render_ipyleaflet` / `render_leafmap`)

## Overview

`pip install 'shinywidgets[ipyleaflet]' 'localtileserver>=1.0.0'`. Turn a
local GeoTIFF or COG into pan/zoom-able slippy-map tiles, served from your
own Shiny process — no separate tile service, no upload, and it works
deployed. There is no dedicated `render_localtileserver`: a `TileClient`
builds an ordinary `ipyleaflet.TileLayer` (via `get_leaflet_tile_layer()`),
so it rides on [`render_ipyleaflet`](ipyleaflet.md) or
[`render_leafmap`](leafmap.md) like any other layer. Reach for
plain ipyleaflet/lonboard instead for vector data (points, lines,
polygons); `leafmap`'s `add_raster()` is localtileserver under the hood
with a friendlier one-line API.

## Quick start

```python
import ipyleaflet as L
from localtileserver import TileClient, get_leaflet_tile_layer
from shiny.express import ui
from shinywidgets import render_ipyleaflet

# Create at module scope, never inside a render: the first open takes a
# few seconds; later layers on the same server are fast.
client = TileClient("path/to/raster.tif")

ui.page_opts(title="localtileserver quickstart", fillable=True)


@render_ipyleaflet
def map():
    m = L.Map(center=client.center(), zoom=9)
    m.add(get_leaflet_tile_layer(client))
    return m
```

`get_tile_url()`/`get_leaflet_tile_layer()` take `indexes` (1-based band
numbers), `colormap` (a rio-tiler name, lowercase — not matplotlib's),
`vmin`/`vmax`, and `expression` (band math, e.g. `"(b2-b1)/(b2+b1)"`) — all
expressed as URL query parameters.

## Accessors

None of its own — all reactivity comes from the host renderer's accessors
(`clicked()`, `drawn_features()`, `bounds()`, `zoom()`, `center()`; see
`ipyleaflet.md`).

## Updating in place

Mutate `map.widget.layers[...].url` or `.opacity` from a
`@reactive.effect` — the normal ipyleaflet in-place pattern, never a
re-render:

```python
from shiny import reactive


@reactive.effect
def _restyle():
    layer.url = client.get_tile_url(colormap="viridis", vmin=0, vmax=input.vmax())
```

## Gotchas

- **Deployment is handled automatically — no API to call.** shinywidgets
  detects any ipyleaflet layer built from a `TileClient`, mounts a guarded
  reverse proxy at `/proxy/{port}/`, and rewrites the layer's tile URLs
  behind an unguessable per-client token, so it works unchanged on Posit
  Connect/shinyapps.io (where the browser's loopback isn't the server's).
  `SHINYWIDGETS_LOOPBACK_PROXY_DISABLE=1` is the only opt-out.
- **`client.part(bbox)`'s `bounds_crs` defaults to the raster's native
  CRS, not WGS84** — passing lon/lat bounds without `bounds_crs="EPSG:4326"`
  returns a degenerate ~1x1-pixel crop with no error. `client.feature()`
  (GeoJSON input) doesn't have this problem.
- **`client.point(...).array` holds NumPy scalar types** — cast with
  `int(...)`/`float(...)` before displaying, or it shows as `np.uint8(19)`.
- Always construct `TileClient` at module scope — inside a render function,
  every re-render re-opens the file.

**More:** <https://shinywidgets.org/widgets/localtileserver/>
