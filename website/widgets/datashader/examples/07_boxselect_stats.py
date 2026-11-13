# A box-select brush can be smaller and more deliberate than "whatever's
# currently zoomed in" -- hv.streams.BoundsXY fires once per drag, and the
# bounds become a pandas mask over the FULL 500,000-row dataframe (not just
# the pixels datashader drew), so stats like mean fare are exact.
import holoviews as hv
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401
from holoviews.streams import BoundsXY
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

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
pickups["fare"] = rng.gamma(2.0, 6.0, len(pickups))

ui.page_opts(title="Box-select stats on the full data", fillable=True)

selected_bounds = reactive.value(None)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Drag a box (box-select tool is active by default)")

        @render_holoviews
        def plot():
            img = pickups.hvplot.points(
                "lon", "lat", rasterize=True, cnorm="eq_hist", cmap="fire",
                responsive=True, tools=["box_select"],
            ).opts(active_tools=["box_select"])
            # the subscriber's parameter must be named "bounds" -- BoundsXY
            # calls it with that keyword
            BoundsXY(source=img).add_subscriber(lambda bounds: selected_bounds.set(bounds))
            return img

    with ui.card():
        ui.card_header("Stats on the full 500,000-row data")

        @render.ui
        def stats():
            b = selected_bounds()
            if b is None:
                return ui.p("Drag a box to select a region.", class_="text-muted")
            x0, y0, x1, y1 = b
            sel = pickups[pickups.lon.between(x0, x1) & pickups.lat.between(y0, y1)]
            return ui.TagList(
                ui.h5(f"{len(sel):,} of {len(pickups):,} rows"),
                ui.p(f"mean fare: ${sel.fare.mean():.2f}" if len(sel) else "mean fare: -"),
            )
