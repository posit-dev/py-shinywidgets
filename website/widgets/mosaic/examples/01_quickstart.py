# Quick start: a two-plot Mosaic crossfilter dashboard.

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny.express import ui
from shinywidgets import render_mosaic_widget

# The Palmer Penguins dataset (Gorman, Williams & Fraser, 2014), via Allison
# Horst's palmerpenguins package.
PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["species", "flipper_length_mm", "body_mass_g"])

# Brushing either plot sets the "$brush" selection; every plot that reads
# from "penguins" filtered by "$brush" updates together.
spec = {
    "params": {"brush": {"select": "crossfilter"}},
    "vconcat": [
        {
            "plot": [
                {
                    "mark": "dot",
                    "data": {"from": "penguins", "filterBy": "$brush"},
                    "x": "flipper_length_mm",
                    "y": "body_mass_g",
                    "fill": "species",
                    "r": 2.5,
                },
                {"select": "intervalXY", "as": "$brush"},
            ],
            "xDomain": "Fixed",
            "yDomain": "Fixed",
            "width": 600,
            "height": 300,
        },
        {
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
            "height": 150,
        },
    ],
}

ui.page_opts(title="Mosaic quick start", fillable=True)

with ui.card(full_screen=True):

    @render_mosaic_widget
    def dashboard():
        return MosaicWidget(spec, data={"penguins": penguins})
