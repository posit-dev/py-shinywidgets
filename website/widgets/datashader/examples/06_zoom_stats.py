# Re-aggregation on zoom is automatic -- hvPlot's rasterize=True attaches its
# own internal hv.streams.RangeXY to the DynamicMap, so scrolling to zoom
# re-runs datashader for just the visible region with no code to write.
# This example also reads that same internal RangeXY stream into Shiny, to
# show a "points in view" stat computed on the full data (not just the
# rasterized pixels). The subscriber stores the range tuple itself (an
# idempotent `.set()`) rather than a counter -- see the guide's Gotchas
# section for why that distinction matters.
import holoviews as hv
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401
from holoviews.streams import RangeXY
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

N = 1_000_000
LANDMARKS = {
    "Times Square": (40.758, -73.985, 0.010),
    "Wall Street": (40.706, -74.009, 0.006),
    "JFK Airport": (40.641, -73.778, 0.020),
    "LaGuardia": (40.777, -73.872, 0.015),
    "Central Park": (40.782, -73.965, 0.015),
}
rng = np.random.default_rng(0)
names = list(LANDMARKS)
weights = rng.dirichlet(np.ones(len(names)) * 3)
counts = rng.multinomial(N, weights)
lat, lon = [], []
for name, c in zip(names, counts):
    lat0, lon0, spread = LANDMARKS[name]
    lat.append(rng.normal(lat0, spread, c))
    lon.append(rng.normal(lon0, spread, c))
pickups = pd.DataFrame({"lat": np.concatenate(lat), "lon": np.concatenate(lon)})

ui.page_opts(title="Zoom stats", fillable=True)

view_range = reactive.value(None)


@render_holoviews
def plot():
    img = pickups.hvplot.points(
        "lon", "lat", rasterize=True, cnorm="eq_hist", cmap="fire", responsive=True,
    )
    rng_stream = next(s for s in img.streams if isinstance(s, RangeXY))
    rng_stream.add_subscriber(lambda x_range, y_range: view_range.set((x_range, y_range)))
    return img


@render.text
def n_in_view():
    r = view_range()
    if r is None or r[0][0] is None:
        return f"{len(pickups):,} in view (full extent)"
    (x0, x1), (y0, y1) = r
    sel = pickups[pickups.lon.between(x0, x1) & pickups.lat.between(y0, y1)]
    return f"{len(sel):,} in view"
