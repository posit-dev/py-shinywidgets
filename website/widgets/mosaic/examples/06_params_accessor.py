# `dashboard.params()`: read the dashboard's current selection as a Python dict.

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny.express import render, ui
from shinywidgets import render_mosaic_widget

PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["flipper_length_mm"])

spec = {
    "params": {"brush": {"select": "crossfilter"}},
    "plot": [
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
    "height": 220,
}

ui.page_opts(title="params() accessor", fillable=True)

with ui.card(full_screen=True):

    @render_mosaic_widget
    def dashboard():
        return MosaicWidget(spec, data={"penguins": penguins})


with ui.card():
    ui.card_header("dashboard.params()")

    @render.code
    def raw_params():
        return str(dashboard.params())
