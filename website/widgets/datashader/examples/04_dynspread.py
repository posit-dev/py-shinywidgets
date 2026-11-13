# A sparse, uniformly-scattered layer (stranded dropoffs far from the main
# cluster) rasterizes to isolated single pixels that are easy to miss at a
# normal screen density. dynspread grows isolated pixels until they're a few
# pixels wide, without doing anything to dense regions where pixels already
# overlap. xlim/ylim below zoom into a sparse corner so the effect is visible
# without needing to zoom interactively.
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401
from shiny.express import ui

from shinywidgets import render_holoviews

rng = np.random.default_rng(1)
dense = pd.DataFrame({
    "lon": rng.normal(-73.985, 0.01, 400_000),
    "lat": rng.normal(40.758, 0.01, 400_000),
})
sparse = pd.DataFrame({
    "lon": rng.uniform(-74.05, -73.75, 4_000),
    "lat": rng.uniform(40.60, 40.85, 4_000),
})
pts = pd.concat([dense, sparse], ignore_index=True)

XLIM, YLIM = (-73.82, -73.76), (40.74, 40.80)

ui.page_opts(title="dynspread", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("rasterize only -- isolated points are 1px, easy to miss")

        @render_holoviews
        def no_spread():
            return pts.hvplot.points(
                "lon", "lat", rasterize=True, cnorm="eq_hist", cmap="fire",
                responsive=True, xlim=XLIM, ylim=YLIM,
            )

    with ui.card(full_screen=True):
        ui.card_header("+ dynspread(max_px=6) -- isolated points become visible dots")

        @render_holoviews
        def with_spread():
            return pts.hvplot.points(
                "lon", "lat", rasterize=True, dynspread=True, max_px=6,
                cnorm="eq_hist", cmap="fire", responsive=True,
                xlim=XLIM, ylim=YLIM,
            )
