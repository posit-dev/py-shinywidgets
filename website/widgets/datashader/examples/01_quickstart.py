# A million synthetic ride-hail pickups, clustered around real NYC landmarks
# (Times Square, Wall Street, JFK, LaGuardia, Central Park) with a Gaussian
# spread around each -- rasterize=True turns them into a single image-sized
# grid on the server, so the browser never sees more than one plot's worth
# of pixels no matter how many rows went in.
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401 -- registers the .hvplot accessor
from shiny.express import ui

from shinywidgets import render_holoviews

N = 1_000_000
LANDMARKS = {
    "Times Square": (40.758, -73.985, 0.010),
    "Wall Street": (40.706, -74.009, 0.006),
    "JFK Airport": (40.641, -73.778, 0.020),
    "LaGuardia": (40.777, -73.872, 0.015),
    "Central Park": (40.782, -73.965, 0.015),
    "Williamsburg": (40.714, -73.957, 0.012),
    "Astoria": (40.772, -73.930, 0.012),
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

ui.page_opts(title=f"{N:,} synthetic ride-hail pickups", fillable=True)


@render_holoviews
def plot():
    return pickups.hvplot.points(
        "lon", "lat", rasterize=True, cnorm="eq_hist", cmap="fire",
        responsive=True, colorbar=True, title="Pickup density",
    )
