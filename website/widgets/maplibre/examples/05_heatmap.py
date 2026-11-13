import requests
from maplibre import Layer, LayerType, Map, MapOptions
from maplibre.basemaps import Carto
from maplibre.sources import GeoJSONSource
from shiny.express import ui
from shinywidgets import render_maplibre

# ~6,100 earthquakes (magnitude and location), maplibre's own heatmap-tutorial dataset
EARTHQUAKES = requests.get(
    "https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson"
).json()

ui.page_opts(fillable=True)

with ui.card(full_screen=True):

    @render_maplibre
    def heatmap():
        m = Map(MapOptions(style=Carto.DARK_MATTER, center=(0, 20), zoom=1.3))
        m.add_source("quakes", GeoJSONSource(data=EARTHQUAKES))
        m.add_layer(
            Layer(
                id="quakes-heat",
                type=LayerType.HEATMAP,
                source="quakes",
                paint={
                    "heatmap-weight": ["interpolate", ["linear"], ["get", "mag"], 0, 0, 8, 1],
                    "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 0, 1, 9, 3],
                    "heatmap-color": [
                        "interpolate", ["linear"], ["heatmap-density"],
                        0, "rgba(33,102,172,0)", 0.2, "#67a9cf", 0.4, "#d1e5f0",
                        0.6, "#fddbc7", 0.8, "#ef8a62", 1, "#b2182b",
                    ],  # fmt: skip
                    "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 0, 2, 9, 25],
                },
            )
        )
        return m
