# A density raster over 1 million rows, crossfiltered with a histogram.
#
# Mosaic never ships raw rows to the browser for a `raster` mark: it asks
# DuckDB to pre-aggregate into pixel bins, so the plot renders and rebrushes
# in well under a second regardless of row count.
#
# 1M synthetic rows (a real dataset this large and this shape isn't readily
# available as a small download): carrier-free flight hour/delay pairs.

from __future__ import annotations

import numpy as np
import pandas as pd
from mosaic_widget import MosaicWidget
from shiny.express import ui
from shinywidgets import render_mosaic_widget

rng = np.random.default_rng(0)
n = 1_000_000
hour = rng.uniform(0, 24, n)
delay = rng.gamma(2.0, 8.0, n) - 10 + np.where(hour > 16, (hour - 16) * 2, 0)
flights = pd.DataFrame({"hour": hour, "delay": np.clip(delay, -20, 120)})

spec = {
    "params": {"brush": {"select": "crossfilter"}},
    "vconcat": [
        {
            "plot": [
                {
                    "mark": "raster",
                    "data": {"from": "flights"},
                    "x": "hour",
                    "y": "delay",
                    "fill": "density",
                },
                {"select": "intervalXY", "as": "$brush"},
            ],
            "xDomain": [0, 24],
            "yDomain": [-20, 120],
            "colorScale": "symlog",
            "colorScheme": "turbo",
            "width": 600,
            "height": 280,
        },
        {
            "plot": [
                {
                    "mark": "rectY",
                    "data": {"from": "flights", "filterBy": "$brush"},
                    "x": {"bin": "hour"},
                    "y": {"count": ""},
                    "fill": "steelblue",
                    "inset": 0.5,
                },
            ],
            "xDomain": [0, 24],
            "width": 600,
            "height": 120,
        },
    ],
}

ui.page_opts(title="Scale: 1M rows", fillable=True)

with ui.card(full_screen=True):

    @render_mosaic_widget
    def dashboard():
        return MosaicWidget(spec, data={"flights": flights})
