# Datashader zoom template: a million-point scatter that re-aggregates on
# every pan/zoom, with a live "points in view" readout computed on the full
# data via the rasterize operation's own internal RangeXY stream.
# template | adapt this for any big lat/lon or x/y scatter
# run: uv run shiny run gallery/template_zoom_reaggregate.py
# data: synthetic, clustered around real NYC landmarks (see guide.md)
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
points = pd.DataFrame({"lat": np.concatenate(lat), "lon": np.concatenate(lon)})

ui.page_opts(title=f"{N:,} points -- pan or zoom to re-aggregate", fillable=True)

view_range = reactive.value(None)

with ui.card(full_screen=True):

    @render_holoviews
    def plot():
        img = points.hvplot.points(
            "lon", "lat", rasterize=True, cnorm="eq_hist", cmap="fire",
            responsive=True, colorbar=True,
        )
        rng_stream = next(s for s in img.streams if isinstance(s, RangeXY))
        rng_stream.add_subscriber(lambda x_range, y_range: view_range.set((x_range, y_range)))
        return img

    @render.text
    def n_in_view():
        r = view_range()
        if r is None or r[0][0] is None:
            return f"{len(points):,} points in view"
        (x0, x1), (y0, y1) = r
        sel = points[points.lon.between(x0, x1) & points.lat.between(y0, y1)]
        return f"{len(sel):,} points in view"
