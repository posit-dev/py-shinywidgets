# Title: Crossfilter starter
# Description: A clean, adaptable two-chart Mosaic crossfilter with a linked
#   summary table. Habits worth copying: fixed domains, a background context
#   layer, and one shared @reactive.calc for the selected data.
# Bucket: template
# Run: uv run --no-sync shiny run docs/widget-guides/mosaic/gallery/template_crossfilter_starter.py
# Data: Palmer Penguins (palmerpenguins), fetched from a stable GitHub URL

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_mosaic_widget

PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["species", "flipper_length_mm", "body_mass_g"])

# Swap in your own table name and columns; everything else -- fixed domains,
# the background context layer, the shared selection -- is worth keeping.
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
            "width": 560,
            "height": 300,
        },
        {
            "plot": [
                {
                    "mark": "rectY",
                    "data": {"from": "penguins"},
                    "x": {"bin": "flipper_length_mm"},
                    "y": {"count": ""},
                    "fill": "#ddd",
                    "inset": 0.5,
                },
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
            "width": 560,
            "height": 150,
        },
    ],
}

ui.page_opts(title="Crossfilter starter", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_mosaic_widget
        def dashboard():
            return MosaicWidget(spec, data={"penguins": penguins})

    with ui.card():
        ui.card_header("Selection")

        @reactive.calc
        def selected():
            dashboard.params()
            return dashboard.data()

        @render.text
        def n_selected():
            (n,) = selected().aggregate("count(*)").fetchall()[0]
            return f"{n} of {len(penguins)} selected"

        @render.data_frame
        def table():
            cols = "species, count(*) AS n, round(avg(body_mass_g)) AS mean_mass"
            df = selected().aggregate(cols, "species").order("species").df()
            return render.DataGrid(df)
