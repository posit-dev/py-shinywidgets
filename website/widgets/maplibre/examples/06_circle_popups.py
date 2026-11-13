import requests
from maplibre import Layer, LayerType, Map, MapOptions
from maplibre.basemaps import Carto
from maplibre.sources import GeoJSONSource
from shiny.express import ui
from shinywidgets import render_maplibre

EARTHQUAKES = requests.get(
    "https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson"
).json()

ui.page_opts(fillable=True)

with ui.card(full_screen=True):

    @render_maplibre
    def quakes():
        # Centered on the 2017 Chiapas (Mexico) M8.1 earthquake, so there's a
        # large circle right away to click and hover
        m = Map(MapOptions(style=Carto.DARK_MATTER, center=(-93.9067, 15.0356), zoom=5))
        m.add_source("quakes", GeoJSONSource(data=EARTHQUAKES))
        m.add_layer(
            Layer(
                id="quakes-circle",
                type=LayerType.CIRCLE,
                source="quakes",
                # Only the strongest quakes, to keep the map readable
                filter=[">=", ["get", "mag"], 5],
                paint={
                    "circle-radius": ["interpolate", ["linear"], ["get", "mag"], 5, 4, 8, 16],
                    "circle-color": ["interpolate", ["linear"], ["get", "mag"], 5, "#fed976", 8, "#b10026"],
                    "circle-stroke-color": "white",
                    "circle-stroke-width": 1,
                },
            )
        )
        # Hover: client-side tooltip, no Python round trip
        m.add_tooltip("quakes-circle", template="Magnitude {{mag}}")
        # Click: client-side popup with the clicked feature's properties
        m.add_popup("quakes-circle", template="<b>M{{mag}}</b> earthquake")
        return m
