import requests
from maplibre import Layer, LayerType, Map, MapOptions
from maplibre.basemaps import Carto
from maplibre.sources import GeoJSONSource
from shiny.express import ui
from shinywidgets import render_maplibre

STATES = requests.get(
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
).json()

# A data-driven paint expression: color interpolates on each feature's
# `density` property (people per square mile), evaluated entirely in the
# browser -- no Python round trip as the map pans or zooms.
DENSITY_COLOR = [
    "interpolate", ["linear"], ["get", "density"],
    0, "#FFEDA0", 10, "#FED976", 20, "#FEB24C", 50, "#FD8D3C",
    100, "#FC4E2A", 200, "#E31A1C", 500, "#BD0026", 1000, "#800026",
]  # fmt: skip

ui.page_opts(fillable=True)

with ui.card(full_screen=True):

    @render_maplibre
    def choropleth():
        m = Map(MapOptions(style=Carto.POSITRON, center=(-98.5, 39.8), zoom=3.3))
        m.add_source("states", GeoJSONSource(data=STATES))
        m.add_layer(
            Layer(
                id="states-fill",
                type=LayerType.FILL,
                source="states",
                paint={"fill-color": DENSITY_COLOR, "fill-opacity": 0.8},
            )
        )
        m.add_layer(
            Layer(
                id="states-outline",
                type=LayerType.LINE,
                source="states",
                paint={"line-color": "#ffffff", "line-width": 0.5},
            )
        )
        return m
