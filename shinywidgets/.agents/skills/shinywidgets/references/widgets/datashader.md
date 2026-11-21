# Datashader (`render_holoviews`)

## Overview

`pip install 'shinywidgets[holoviews]' datashader hvplot`. There is no
dedicated `render_datashader` — Datashader plots render through
[`@render_holoviews`](holoviews.md), the same decorator as any other
HoloViews/hvPlot object. Use it to aggregate tens of millions of points into
a single image-sized grid on the server, so the browser never sees more
than one plot's worth of pixels no matter how many rows went in.

## Quick start

```python
import hvplot.pandas  # noqa: F401 -- registers the .hvplot accessor
from shiny.express import ui
from shinywidgets import render_holoviews

ui.page_opts(title="Pickup density", fillable=True)


@render_holoviews
def plot():
    return pickups.hvplot.points(
        "lon",
        "lat",
        rasterize=True,
        cnorm="eq_hist",
        cmap="fire",
        responsive=True,
        colorbar=True,
    )
```

`rasterize=True` is the whole integration: hvPlot wraps the points in a
`DynamicMap`, aggregates them into a grid sized to the output's pixels, and
colors it with `cmap`. `cnorm="eq_hist"` (histogram-equalized scaling) keeps
sparse outskirts visible next to dense cores, which a linear scale would
wash out. The underlying rows never leave the server — only the rendered
image does, so the payload stays flat (~2.2 MB at 10K points, ~2.4 MB at
1M) regardless of point count.

## Accessors

None directly — see `holoviews.md` for the general stream-subscriber
pattern (`RangeXY`, `BoundsXY`). Reuse `rasterize()`'s own internal
`RangeXY` stream (`next(s for s in img.streams if isinstance(s, RangeXY))`)
rather than constructing a second one.

## Updating in place

Drive the `DynamicMap` with its stream (`stream.event(...)`), the same
mechanism `holoviews.md` describes — never rebuild the plot to change the
view region.

## Gotchas

- **Build the plot inside the render function, never at module level** —
  a module-level `DynamicMap` is shared by every session; one visitor's
  zoom repaints everyone's plot. The source data frame is fine to load once
  at module level.
- **A `BoundsXY` subscriber's parameter must be named `bounds`.** A
  differently-named parameter raises inside HoloViews' own asyncio task,
  swallowed as "Task exception was never retrieved" in the **server log**
  only — no browser-visible error, so a box-select can silently do nothing.
- **`datashade` can't show a colorbar or hover values; only `rasterize`
  can.** This is by design, not a bug — don't reach for `datashade` for its
  smaller payload and then wonder why hover stopped working.
- Aggregation runs on the server's event loop; a very large aggregation
  briefly delays every other session that process serves (in practice,
  Numba-compiled aggregation stays well under 100ms even at 10M points).

**More:** <https://shinywidgets.org/widgets/datashader/>
