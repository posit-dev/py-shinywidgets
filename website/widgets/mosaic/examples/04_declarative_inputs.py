# Menu, histogram, and table, linked by one selection -- no Python callbacks.

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny.express import ui
from shinywidgets import render_mosaic_widget

PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["species", "flipper_length_mm", "body_mass_g"])

spec = {
    "params": {"species": {"select": "intersect"}},
    "vconcat": [
        {
            "input": "menu",
            "label": "Species",
            "from": "penguins",
            "column": "species",
            "as": "$species",
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
            ],
            "xDomain": "Fixed",
            "width": 600,
            "height": 220,
        },
        {
            "input": "table",
            "from": "penguins",
            "filterBy": "$species",
            "columns": ["species", "flipper_length_mm", "body_mass_g"],
        },
    ],
}

ui.page_opts(title="Declarative inputs", fillable=True)

with ui.card(full_screen=True):

    @render_mosaic_widget
    def dashboard():
        return MosaicWidget(spec, data={"penguins": penguins})
