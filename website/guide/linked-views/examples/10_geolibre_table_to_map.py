from __future__ import annotations

import pandas as pd
from geolibre import Map
from shiny import reactive, render
from shiny.express import ui

from shinywidgets import render_geolibre

ui.page_opts(title="Table selection -> map", fillable=True)

CITIES = pd.DataFrame(
    [
        ("New York", -74.0, 40.7, 8.48),
        ("Los Angeles", -118.2, 34.0, 3.88),
        ("Chicago", -87.6, 41.9, 2.72),
        ("Houston", -95.4, 29.8, 2.31),
        ("Phoenix", -112.1, 33.4, 1.65),
    ],
    columns=["city", "lng", "lat", "population_m"],
)

with ui.layout_columns(col_widths=[5, 7]):
    with ui.card():
        ui.card_header("5 largest US cities")

        @render.data_frame
        def table():
            return render.DataGrid(CITIES[["city", "population_m"]], selection_mode="row")

    with ui.card(full_screen=True):

        @render_geolibre
        def map():
            return Map(center=(-98.5, 39.8), zoom=3.5)


@reactive.effect
def _():
    rows = table.cell_selection()["rows"]
    if not rows:
        return
    row = CITIES.iloc[rows[0]]
    map.widget.set_center(row["lng"], row["lat"], zoom=9)
