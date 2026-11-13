# rasterize=True sends a scalar field with a live colorbar and hover values;
# datashade=True bakes the colors into an RGBA image server-side instead --
# no colorbar or hover, but a smaller payload (see the guide's payload table).
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401
from shiny.express import ui

from shinywidgets import render_holoviews

N = 500_000
LANDMARKS = {
    "Times Square": (40.758, -73.985, 0.010),
    "Wall Street": (40.706, -74.009, 0.006),
    "JFK Airport": (40.641, -73.778, 0.020),
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

ui.page_opts(title="rasterize vs datashade", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("rasterize=True -- colorbar + hover values")

        @render_holoviews
        def raster():
            return pickups.hvplot.points(
                "lon", "lat", rasterize=True, cnorm="eq_hist", cmap="fire",
                responsive=True, colorbar=True,
            )

    with ui.card(full_screen=True):
        ui.card_header("datashade=True -- no colorbar/hover, smaller payload")

        @render_holoviews
        def shade():
            return pickups.hvplot.points(
                "lon", "lat", datashade=True, cnorm="eq_hist", cmap="fire",
                responsive=True,
            )
