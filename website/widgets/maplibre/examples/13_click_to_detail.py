import numpy as np
import requests
from maplibre import Layer, LayerType, Map, MapOptions
from maplibre.basemaps import Carto
from maplibre.sources import GeoJSONSource
from shiny.express import render, ui
from shinywidgets import render_maplibre

EARTHQUAKES = requests.get(
    "https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson"
).json()
QUAKES = [f for f in EARTHQUAKES["features"] if f["properties"]["mag"] >= 5]
LNG = np.array([f["geometry"]["coordinates"][0] for f in QUAKES])
LAT = np.array([f["geometry"]["coordinates"][1] for f in QUAKES])

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_maplibre
        def quakes():
            # Centered on the 2017 Chiapas (Mexico) M8.1 earthquake
            m = Map(MapOptions(style=Carto.DARK_MATTER, center=(-93.9067, 15.0356), zoom=5))
            m.add_source("quakes", GeoJSONSource(data=EARTHQUAKES))
            m.add_layer(
                Layer(
                    id="quakes-circle",
                    type=LayerType.CIRCLE,
                    source="quakes",
                    filter=[">=", ["get", "mag"], 5],
                    paint={"circle-radius": 6, "circle-color": "#fd8d3c"},
                )
            )
            return m

    with ui.card():
        ui.card_header("Clicked earthquake")

        @render.ui
        def detail():
            # `clicked()` is a bare lng/lat -- maplibre doesn't report which
            # feature was clicked, so find the nearest one in Python.
            ll = quakes.clicked()
            if ll is None:
                return "Click a dot on the map."
            i = int(np.argmin((LNG - ll["lng"]) ** 2 + (LAT - ll["lat"]) ** 2))
            f = QUAKES[i]
            return ui.tags.ul(
                ui.tags.li(f"Magnitude: {f['properties']['mag']}"),
                ui.tags.li(f"Location: {LAT[i]:.2f}, {LNG[i]:.2f}"),
            )
