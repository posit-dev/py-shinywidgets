# A crossfiltered histogram with a gray "all rows" layer for context.

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny.express import ui
from shinywidgets import render_mosaic_widget

PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["flipper_length_mm"])

spec = {
    "params": {"brush": {"select": "crossfilter"}},
    "plot": [
        # Background layer: every row, unfiltered, so the shape of the whole
        # dataset stays visible while brushing.
        {
            "mark": "rectY",
            "data": {"from": "penguins"},
            "x": {"bin": "flipper_length_mm"},
            "y": {"count": ""},
            "fill": "#ddd",
            "inset": 0.5,
        },
        # Foreground layer: only the brushed rows, drawn on top.
        {
            "mark": "rectY",
            "data": {"from": "penguins", "filterBy": "$brush"},
            "x": {"bin": "flipper_length_mm"},
            "y": {"count": ""},
            "fill": "steelblue",
            "inset": 0.5,
        },
        {"select": "intervalX", "as": "$brush"},
    ],
    "xDomain": "Fixed",
    "width": 600,
    "height": 300,
}

ui.page_opts(title="Context layers", fillable=True)

with ui.card(full_screen=True):

    @render_mosaic_widget
    def dashboard():
        return MosaicWidget(spec, data={"penguins": penguins})
