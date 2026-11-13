# Linked view + read on demand: export rows matching one selection, picked
# with filter_by=, from a two-selection crossfilter dashboard.
#
# Pairs with: quak (same read-on-demand export pattern, there on
# table.data()). The download handler reads dashboard.data() only when the
# user clicks Download -- no warm-up needed, since the accessor is live from
# the moment the dashboard renders.

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny import render
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

ui.page_opts(title="Export filtered rows (filter_by=)", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_mosaic_widget
        def dashboard():
            return MosaicWidget(spec, data={"penguins": penguins})

    with ui.card():
        ui.card_header("Export")
        "Rows matching the flipper-length brush only -- filter_by picks that one selection, ignoring any species clicked above."

        @render.download_button(filename="flipper_selected.csv", label="Download CSV")
        def download():
            yield dashboard.data(filter_by="flipper").df().to_csv(index=False)
