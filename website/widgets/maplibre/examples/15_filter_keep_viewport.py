import requests
from maplibre import Layer, LayerType, Map, MapOptions
from maplibre.basemaps import Carto
from maplibre.sources import GeoJSONSource
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_maplibre

EARTHQUAKES = requests.get(
    "https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson"
).json()

ui.page_opts(fillable=True)
ui.input_slider("min_mag", "Minimum magnitude", 0, 8, 0, step=0.5)

with ui.card(full_screen=True):

    @render_maplibre
    def quakes():
        m = Map(MapOptions(style=Carto.DARK_MATTER, center=(0, 20), zoom=1.2))
        m.add_source("quakes", GeoJSONSource(data=EARTHQUAKES))
        m.add_layer(
            Layer(
                id="quakes-circle",
                type=LayerType.CIRCLE,
                source="quakes",
                paint={"circle-radius": 3, "circle-color": "#fd8d3c", "circle-opacity": 0.7},
            )
        )
        return m


@reactive.effect
def _filter():
    # set_filter() restyles the existing layer; it never rebuilds the map, so
    # wherever the user has panned and zoomed to stays exactly where it was.
    quakes.widget.set_filter("quakes-circle", [">=", ["get", "mag"], input.min_mag()])
