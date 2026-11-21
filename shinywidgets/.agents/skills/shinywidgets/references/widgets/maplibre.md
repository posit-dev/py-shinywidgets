# MapLibre (`render_maplibre`)

## Overview

`pip install 'shinywidgets[maplibre]'`. Styled vector-tile maps with 3D
extrusions, live restyling, and deck.gl layers, all driven from Python.
Accepts a `maplibre.Map` (coerced to a `MapWidget`) or a `MapWidget`
directly. Comfortable to a few hundred thousand features. The recommended
migration target for deprecated `render_pydeck` (via `add_deck_layers()`).

## Quick start

```python
from maplibre import Map
from shinywidgets import render_maplibre


@render_maplibre
def map():
    return Map()
```

In a filling layout the map fills its container unless the `MapWidget` has
an explicit `height`.

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `view_state()` | `{"center": {lng, lat}, "zoom", "bounds": {_sw, _ne}, "bearing", "pitch"}` | cancels until the browser's first report |
| `clicked()` | `{lng, lat}` of the last click (not which feature was hit) | `None` |
| `drawn_features()` | GeoJSON Feature dicts from a MapboxDraw control | `[]` |

`view_state()` reports only when a pan/zoom *finishes* (not per animation
frame), so it's not rate-limited by default; to rate-limit a burst of
programmatic `fly_to()` calls, use `reactive_read(map.widget, "view_state")`
instead. `clicked()`/`drawn_features()` are kept/reset the same way as
ipyleaflet's. Feature-level click/hover events aren't synced. For other
traits (e.g. MapboxDraw's `draw_features_selected`), use `map.read(...)`.

## Updating in place

Call methods on `.widget` — these are sent to the browser as commands, so
assigning traits directly (e.g. `map_options` after rendering) has no
effect:

```python
from shiny import reactive


@reactive.effect
def _restyle():
    map.widget.set_paint_property("my-layer", "fill-color", new_color)
```

`set_paint_property()`, `set_filter()`, `set_data()`, `fit_bounds()`, and
`add_call()` (for any MapLibre GL JS map method) all work this way.

## Gotchas

- **Upstream bug, lonboard interop**: rendering a lonboard map and a
  maplibre map on the same page crashes lonboard's view (`deck.gl -
  multiple versions detected`, conflicting bundled deck.gl copies) — keep
  them on separate pages.
- A queued `add_call()` (e.g. a style applied before a widget swap) is
  delivered once the new widget's comm opens, not dropped.

**More:** <https://shinywidgets.org/widgets/maplibre/>
