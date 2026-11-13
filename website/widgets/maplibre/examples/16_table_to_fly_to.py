import pandas as pd
import requests
from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny import reactive, render
from shiny.express import ui
from shinywidgets import render_maplibre

EARTHQUAKES = requests.get(
    "https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson"
).json()
TOP10 = (
    pd.DataFrame(
        {
            "mag": [f["properties"]["mag"] for f in EARTHQUAKES["features"]],
            "lng": [f["geometry"]["coordinates"][0] for f in EARTHQUAKES["features"]],
            "lat": [f["geometry"]["coordinates"][1] for f in EARTHQUAKES["features"]],
        }
    )
    .nlargest(10, "mag")
    .reset_index(drop=True)
)

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[5, 7]):
    with ui.card():
        ui.card_header("10 strongest earthquakes")

        @render.data_frame
        def table():
            return render.DataGrid(TOP10[["mag"]], selection_mode="row")

    with ui.card(full_screen=True):

        @render_maplibre
        def quakes():
            return Map(MapOptions(style=Carto.DARK_MATTER, center=(0, 20), zoom=1.2))


@reactive.effect
def _fly_to():
    rows = table.cell_selection()["rows"]
    if not rows:
        return
    row = TOP10.iloc[rows[0]]
    quakes.widget.add_call("flyTo", {"center": [row["lng"], row["lat"]], "zoom": 5})
