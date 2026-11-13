# Linked view: a Mosaic brush feeds a small plotly bar chart.
#
# Pairs with: plotly. Unlike the lonboard example, this chart is cheap enough
# to re-render on every brush move -- `render_plotly` just needs a Figure
# object, built here from `dashboard.data()`.

from __future__ import annotations

import pandas as pd
import plotly.express as px
from mosaic_widget import MosaicWidget
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_mosaic_widget, render_plotly

PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["species", "flipper_length_mm"])

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
    "width": 500,
    "height": 220,
}

ui.page_opts(title="Mosaic + plotly", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_mosaic_widget
        def dashboard():
            return MosaicWidget(spec, data={"penguins": penguins})

    with ui.card(full_screen=True):

        @render_plotly
        def species_counts():
            dashboard.params()
            counts = dashboard.data().aggregate("species, count(*) AS n", "species").df()
            return px.bar(counts, x="species", y="n", color="species", title="Selected, by species")
