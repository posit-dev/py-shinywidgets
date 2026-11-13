# The same idea, done entirely inside one widget: Mosaic's own crossfilter.
#
# Same Gaia data and the same shape as 18_datashader_brush_summaries.py (a
# raster sky map plus magnitude/parallax histograms), but with no Python
# round trip at all. Mosaic compiles each histogram's intervalX brush into a
# DuckDB query that updates every OTHER mark's filterBy (the raster and the
# other histogram) -- including re-binning the raster -- entirely in the
# browser-to-DuckDB loop. Brushing either histogram narrows the raster and
# the other histogram's bars with no visible lag, regardless of the 5
# million rows behind it.
from __future__ import annotations

from pathlib import Path

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny.express import ui

from shinywidgets import render_mosaic_widget

DATA_PATH = Path(__file__).parent.parent / "data" / "gaia-5m.parquet"
gaia = pd.read_parquet(DATA_PATH, columns=["l", "b", "parallax", "phot_g_mean_mag"])
# A few percent of rows have a noisy, far-out-of-range parallax measurement
# (Gaia parallaxes can be negative or implausibly large for faint, distant
# stars). Clip -- don't drop -- those rows so DuckDB's automatic bin width
# for the histogram below is set by the visible [-3, 5] domain, not by a
# handful of outliers out past 100.
gaia["parallax"] = gaia["parallax"].clip(-5, 8)

spec = {
    "params": {"brush": {"select": "crossfilter"}},
    "vconcat": [
        {
            "plot": [
                {
                    "mark": "raster",
                    "data": {"from": "gaia", "filterBy": "$brush"},
                    "x": "l",
                    "y": "b",
                    "fill": "density",
                },
            ],
            "xDomain": [0, 360],
            "yDomain": [-90, 90],
            "colorScale": "symlog",
            "colorScheme": "turbo",
            "width": 760,
            "height": 300,
        },
        {
            "hconcat": [
                {
                    "plot": [
                        {
                            "mark": "rectY",
                            "data": {"from": "gaia", "filterBy": "$brush"},
                            "x": {"bin": "phot_g_mean_mag"},
                            "y": {"count": ""},
                            "fill": "#4c78a8",
                            "inset": 0.5,
                        },
                        {"select": "intervalX", "as": "$brush"},
                    ],
                    "xDomain": [14, 21.5],
                    "width": 370,
                    "height": 220,
                },
                {
                    "plot": [
                        {
                            "mark": "rectY",
                            "data": {"from": "gaia", "filterBy": "$brush"},
                            "x": {"bin": "parallax"},
                            "y": {"count": ""},
                            "fill": "#f58518",
                            "inset": 0.5,
                        },
                        {"select": "intervalX", "as": "$brush"},
                    ],
                    "xDomain": [-3, 5],
                    "width": 370,
                    "height": 220,
                },
            ],
        },
    ],
}

ui.page_opts(title="Mosaic: brushing in the browser, no Python round trip", fillable=True)

with ui.card(full_screen=True):

    @render_mosaic_widget
    def dashboard():
        return MosaicWidget(spec, data={"gaia": gaia})
