import requests
from maplibre import Layer, LayerType, Map, MapOptions
from maplibre.basemaps import Carto
from maplibre.sources import GeoJSONSource
from shiny.express import ui
from shinywidgets import render_maplibre

STATES = requests.get(
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
).json()

DENSITY_COLOR = [
    "interpolate", ["linear"], ["get", "density"],
    0, "#FFEDA0", 10, "#FED976", 20, "#FEB24C", 50, "#FD8D3C",
    100, "#FC4E2A", 200, "#E31A1C", 500, "#BD0026", 1000, "#800026",
]  # fmt: skip
# Same property drives extrusion height (meters), exaggerated for visibility
DENSITY_HEIGHT = [
    "interpolate", ["linear"], ["get", "density"],
    0, 0, 10, 20000, 100, 120000, 1000, 600000,
]  # fmt: skip

ui.page_opts(fillable=True)

with ui.card(full_screen=True):

    @render_maplibre
    def extrusion():
        m = Map(
            MapOptions(
                style=Carto.DARK_MATTER,
                center=(-98.5, 39.8),
                zoom=3.3,
                pitch=55,
                bearing=-10,
            )
        )
        m.add_source("states", GeoJSONSource(data=STATES))
        m.add_layer(
            Layer(
                id="states-extrude",
                type=LayerType.FILL_EXTRUSION,
                source="states",
                paint={
                    "fill-extrusion-color": DENSITY_COLOR,
                    "fill-extrusion-height": DENSITY_HEIGHT,
                    "fill-extrusion-opacity": 0.9,
                },
            )
        )
        return m
