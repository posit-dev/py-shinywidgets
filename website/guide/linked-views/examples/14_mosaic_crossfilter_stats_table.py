# Linked view: a brush drives a stat line and an aggregated table.
#
# Pairs with: render-widget (plain Shiny outputs, no other widget library
# needed) -- the simplest possible consumer of a Mosaic selection.

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_mosaic_widget

PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["species", "flipper_length_mm", "body_mass_g"])

spec = {
    "params": {"brush": {"select": "crossfilter"}},
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
    "height": 320,
}

ui.page_opts(title="Linked stats + table", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_mosaic_widget
        def dashboard():
            return MosaicWidget(spec, data={"penguins": penguins})

    with ui.card():
        ui.card_header("Selected penguins")

        @reactive.calc
        def selected():
            dashboard.params()
            return dashboard.data()

        @render.text
        def n_selected():
            (n,) = selected().aggregate("count(*)").fetchall()[0]
            return f"{n} of {len(penguins)} selected"

        @render.data_frame
        def by_species():
            cols = "species, count(*) AS n, round(avg(body_mass_g)) AS mean_mass"
            df = selected().aggregate(cols, "species").order("species").df()
            return render.DataGrid(df)
