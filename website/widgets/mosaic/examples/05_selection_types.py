# Two different selection types (toggle + interval) crossfiltering each other.

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny.express import ui
from shinywidgets import render_mosaic_widget

PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["species", "flipper_length_mm"])

spec = {
    "params": {
        "species": {"select": "intersect"},
        "flipper": {"select": "intersect"},
    },
    "hconcat": [
        {
            "plot": [
                {
                    "mark": "barX",
                    "data": {"from": "penguins", "filterBy": "$flipper"},
                    "x": {"count": ""},
                    "y": "species",
                    "fill": "steelblue",
                    "sort": {"y": "-x"},
                },
                {"select": "toggleY", "as": "$species"},
            ],
            "yLabel": None,
            "marginLeft": 90,
            "width": 280,
            "height": 160,
        },
        {
            "plot": [
                {
                    "mark": "rectY",
                    "data": {"from": "penguins", "filterBy": "$species"},
                    "x": {"bin": "flipper_length_mm"},
                    "y": {"count": ""},
                    "fill": "steelblue",
                    "inset": 0.5,
                },
                {"select": "intervalX", "as": "$flipper"},
            ],
            "xDomain": "Fixed",
            "width": 340,
            "height": 160,
        },
    ],
}

ui.page_opts(title="Selection types", fillable=True)

with ui.card(full_screen=True):

    @render_mosaic_widget
    def dashboard():
        return MosaicWidget(spec, data={"penguins": penguins})
