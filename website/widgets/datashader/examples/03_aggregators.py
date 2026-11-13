# Three aggregators over the same 500,000 rows: count (density), mean of a
# numeric column (fare), and count_cat (density per category, with a color
# key and legend instead of a colorbar).
import datashader as ds
import holoviews as hv
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401
from shiny.express import ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

N = 500_000
LANDMARKS = {
    "Times Square": (40.758, -73.985, 0.010),
    "Wall Street": (40.706, -74.009, 0.006),
    "JFK Airport": (40.641, -73.778, 0.020),
    "LaGuardia": (40.777, -73.872, 0.015),
}
rng = np.random.default_rng(0)
names = list(LANDMARKS)
weights = rng.dirichlet(np.ones(len(names)) * 3)
counts = rng.multinomial(N, weights)
lat, lon, place = [], [], []
for name, c in zip(names, counts):
    lat0, lon0, spread = LANDMARKS[name]
    lat.append(rng.normal(lat0, spread, c))
    lon.append(rng.normal(lon0, spread, c))
    place.extend([name] * c)
pickups = pd.DataFrame({"lat": np.concatenate(lat), "lon": np.concatenate(lon), "place": pd.Categorical(place)})
# JFK fares run higher, on top of the base gamma-distributed fare
pickups["fare"] = rng.gamma(2.0, 6.0, len(pickups)) + (pickups.place == "JFK Airport") * 40

ui.page_opts(title="Aggregators", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("count (default)")

        @render_holoviews
        def by_count():
            return pickups.hvplot.points(
                "lon", "lat", rasterize=True, aggregator="count",
                cnorm="eq_hist", cmap="fire", responsive=True, colorbar=True,
            )

    with ui.card(full_screen=True):
        ui.card_header("mean(fare)")

        @render_holoviews
        def by_mean():
            return pickups.hvplot.points(
                "lon", "lat", rasterize=True, aggregator=ds.mean("fare"),
                cmap="viridis", responsive=True, colorbar=True,
                clabel="mean fare ($)",
            )

    with ui.card(full_screen=True):
        ui.card_header("count_cat(place)")

        @render_holoviews
        def by_cat():
            return pickups.hvplot.points(
                "lon", "lat", datashade=True, aggregator=ds.count_cat("place"),
                color_key="Category10", responsive=True, legend="top_right",
            )
