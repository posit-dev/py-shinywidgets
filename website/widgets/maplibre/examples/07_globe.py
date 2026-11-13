import requests
from maplibre import Layer, LayerType, Map, MapOptions
from maplibre.basemaps import Carto
from maplibre.controls import GlobeControl
from maplibre.sources import GeoJSONSource
from shiny.express import ui
from shinywidgets import render_maplibre

EARTHQUAKES = requests.get(
    "https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson"
).json()

ui.page_opts(fillable=True)

with ui.card(full_screen=True):

    @render_maplibre
    def globe():
        m = Map(
            MapOptions(style=Carto.DARK_MATTER, center=(0, 20), zoom=1.2),
            controls=[GlobeControl()],  # lets the user toggle globe <-> flat map
        )
        # MapLibre's 3D globe projection is named "vertical-perspective"; pass
        # the string, not maplibre.projection.ProjectionType.GLOBE -- that
        # enum member isn't JSON-serializable and silently drops every other
        # queued call for this map (see the guide's Gotchas section)
        m.set_projection("vertical-perspective")
        m.add_source("quakes", GeoJSONSource(data=EARTHQUAKES))
        m.add_layer(
            Layer(
                id="quakes-circle",
                type=LayerType.CIRCLE,
                source="quakes",
                filter=[">=", ["get", "mag"], 5],
                paint={"circle-radius": 4, "circle-color": "#fd8d3c"},
            )
        )
        return m
