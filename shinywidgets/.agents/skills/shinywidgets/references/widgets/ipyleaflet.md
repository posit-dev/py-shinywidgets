# ipyleaflet (`render_ipyleaflet`)

## Overview

`pip install 'shinywidgets[ipyleaflet]'`. A fully interactive Leaflet map
in Shiny — draw shapes, click features, and drag markers, all wired back to
Python. Accepts an `ipyleaflet.Map` (or a subclass, e.g. `leafmap.leafmap.Map`
— see `leafmap.md`). DOM-based: prefer one GeoJSON layer over many
`Marker`s past a few hundred points.

## Quick start

```python
import ipyleaflet
from shinywidgets import render_ipyleaflet


@render_ipyleaflet
def map():
    return ipyleaflet.Map(center=(51.48, 0), zoom=12)
```

In a filling layout the map fills its container unless it has its own
height (e.g. `Layout(height="300px")`); a subclass's own default height
(leafmap's 600px) is treated as unset.

## Accessors

Coordinates are `[lat, lng]`, as ipyleaflet reports them (lonboard is
`(lng, lat)`).

| Accessor | Returns | Before first interaction |
|---|---|---|
| `bounds()` | `((south, west), (north, east))` viewport | cancels until the browser first reports |
| `zoom()` | Current zoom level | — |
| `center()` | `[lat, lng]` | — |
| `clicked()` | `{"type": "click", "coordinates": [lat, lng], "location": ...}` | `None` |
| `drawn_features()` | GeoJSON Feature dicts drawn on a `DrawControl` | `[]` |

`bounds()` updates once per pan/zoom, at gesture end. `clicked()` is kept
across re-renders until the user clicks the new map; a double-click
publishes once (the second click has the same coordinates). Marker clicks
don't bubble to the map — use a layer's own `on_click` for those.
`drawn_features()` raises `TypeError` if the map has no `DrawControl` —
add one with `m.add(DrawControl())`.

## Updating in place

Mutate `.widget`'s layers/traits (style, visibility, basemap, zoom, center)
directly — this is cheap for most traits, but see the gotcha below:

```python
from shiny import reactive


@reactive.effect
def _recenter():
    map.widget.center = (new_lat, new_lng)
    map.widget.zoom = 10
```

## Gotchas

- **Toggling `layer.visible` is cheap (~444 bytes); setting `layer.style`
  on a GeoJSON layer is not** — it costs almost as much as a full
  re-render, because ipyleaflet's `GeoJSON` rebuilds its entire `data`
  trait on every style change (an upstream behavior, not a shinywidgets
  limitation). For cheap restyling of many features, prefer a vector-tile
  map (`maplibre`, `lonboard`).
- Reading `bounds()` on a hidden (e.g. inactive-tab) map reports the
  browser's last known bounds, which ipyleaflet may corrupt while hidden —
  guard with your own visibility check if that matters.
- Only the chrome (zoom control, attribution strip) follows
  `ui.input_dark_mode()`; the tile imagery itself doesn't.

**More:** <https://shinywidgets.org/widgets/ipyleaflet/>
