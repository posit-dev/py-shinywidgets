# GeoLibre (`render_geolibre`)

## Overview

`pip install 'shinywidgets[geolibre]'`. Embed the full GeoLibre desktop-GIS
app (layer panel, styling, drawing, measuring) in a Shiny output, drive it
from Python, and read its live state back. Accepts a `geolibre.Map`.
shinywidgets serves the bundled app from the Shiny process itself, so it
works in deployed apps, not just locally.

## Quick start

```python
from geolibre import Map
from shinywidgets import render_geolibre


@render_geolibre
def map():
    return Map()
```

In a filling layout the map fills its container unless given a `height`
other than geolibre's default (`"800px"`) — `height` is read once, when
the app loads, so changing `.widget.height` after rendering has no effect
(resize the output's container instead). `geolibre.Map(app_layout=...)`
chooses the app's chrome (`"embed"`, `"full"`, `"maponly"`).

## Accessors

None dedicated — user edits (pan, zoom, add/restyle layers) sync back to
the `project` trait: `map.read("project")` gives the live project, but it
invalidates on every pan/zoom and carries the whole document (including
inlined layer data). For high-frequency interactions, register
`map.widget.on_click()`, `on_selection_change()`, or `on_layer_change()`
inside the render function instead, and have the callback set a
`reactive.value`.

## Updating in place

Methods that edit the map's project work directly:
`add_geojson()`/`add_vector()`/`add_cog()`, `set_center()`/`set_zoom()`,
layer styling (`get_layer(id).set_style()`). **Methods that send a command
and wait for a reply** (`fly_to()`, `fit_bounds()`, `get_center()`,
`get_selected_features()`, `run_algorithm()`, `to_image()`) **can't run
inside a render function, `@reactive.calc`, or `@reactive.effect`** — the
reply only arrives after the current flush finishes, so waiting there
deadlocks. Use the `*_async()` variants inside a `reactive.extended_task`
instead:

```python
from shiny import reactive


@reactive.extended_task
async def _fly():
    await map.widget.fly_to_async(center=(0, 0), zoom=4)
```

Prefer the non-blocking alternative where one exists:
`set_center()`/`fit_project_bounds()` over `fly_to()`/`fit_bounds()`, and
the synced `project` trait over the `get_*()` query methods.

## Gotchas

- **Network access**: local-file layers (`add_cog()`/`add_raster()` of a
  server-side GeoTIFF) are served through a reverse proxy shinywidgets
  mounts, protected by unguessable per-process tokens — basemap tiles and
  remote URLs still need internet access from the browser.
- geolibre < 3.6.1 named the chrome parameter `layout` (shadowing
  ipywidgets' own `Layout` trait); 3.6.1+ renamed it `app_layout`.

**More:** <https://shinywidgets.org/widgets/geolibre/>
