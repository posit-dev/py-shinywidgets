# 200,000 points sent as raw coordinates (left) vs. rasterized to a fixed-size
# image on the server before it ever reaches the browser (right). Both pan and
# zoom the same way, but the rasterized version re-aggregates per view instead
# of shipping every point -- see ../datashader/guide.md for the full story.
import geoviews as gv
import holoviews as hv
import hvplot.pandas  # noqa: F401
import numpy as np
import pandas as pd
from shiny.express import ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

rng = np.random.default_rng(0)
n = 200_000
cities = np.array([(-74, 41), (-0.1, 51.5), (139, 35.7), (28, -26), (151, -34)])
center = cities[rng.integers(0, len(cities), n)]
points = pd.DataFrame(
    center + rng.normal(0, 3.0, (n, 2)), columns=["lon", "lat"]
)

ui.page_opts(title="200,000 points: raw vs. rasterized", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Raw gv.Points (every coordinate shipped)")

        @render_holoviews
        def raw():
            return (gv.tile_sources.EsriWorldDarkGrayBase * gv.Points(points, kdims=["lon", "lat"]).opts(
                size=2, alpha=0.1, color="cyan"
            )).opts(responsive=True)

    with ui.card(full_screen=True):
        ui.card_header("hvPlot rasterize=True (fixed-size image)")

        @render_holoviews
        def rasterized():
            return points.hvplot.points(
                "lon", "lat", geo=True, rasterize=True, dynspread=True,
                cmap="fire", tiles="EsriWorldDarkGrayBase", responsive=True,
            )
