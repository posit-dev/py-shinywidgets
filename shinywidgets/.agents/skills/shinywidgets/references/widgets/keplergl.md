# kepler.gl (`render_keplergl`)

## Overview

`pip install 'shinywidgets[keplergl]'`. Hand users a full
geospatial-analysis studio — auto-layers, filters, 3D hexbins, time
playback — in a Shiny output, and get a reusable `config` back. Accepts a
`pandas.DataFrame`/`geopandas.GeoDataFrame` (coerced to a `KeplerGl` widget
with the data added as a dataset named `"data"`) or a `KeplerGl` widget
directly. Ships a ~12.9 MB JS bundle per fresh render, so in-place config
updates matter more here than almost anywhere else in the roster.

## Quick start

```python
import pandas as pd
from shinywidgets import render_keplergl

cities = pd.DataFrame({"lat": [37.77, 40.71], "lon": [-122.42, -74.01], "city": ["SF", "NYC"]})


@render_keplergl
def map():
    return cities
```

In a filling layout the map resizes to its container unless given a
`height` other than kepler.gl's default (400); an explicit output `height`
takes precedence over the widget's own. **Change the output's size, not
`.widget.height` from Python** — the browser sets `height` to what it
measures.

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `config()` | The map's kepler.gl config (layers, filters, viewport, style) | opt-in; see below |

`config()` is opt-in (`listen_to=["config"]`): kepler.gl syncs the whole
config on every store dispatch — per animation frame while panning/zooming,
with no debounce — so the trait stays muted unless declared. Debounced
250ms by default once enabled. For a one-off read, or to read
`.widget.config` directly, turn native events on app-wide with
`shinywidgets.config(native_events=True)`.

## Updating in place

Use `.widget` to mutate the rendered map — e.g. `.widget.data = ...` is
roughly 1,500x smaller than re-sending the full bundle:

```python
from shiny import reactive

@reactive.effect
def _update_data():
    map.widget.data = {"data": new_df}
```

## Gotchas

- Ships a large (~12.9 MB) JS bundle on every fresh render — prefer
  updating `.data`/`.config` in place over re-rendering whenever possible.
- `config` nests kepler's own config under `config["config"]["mapState"]`
  when read via `leafmap.kepler.Map` (see `leafmap.md`).

**More:** <https://shinywidgets.org/widgets/keplergl/>
