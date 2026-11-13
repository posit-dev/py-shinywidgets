import requests
from maplibre import Layer, LayerType, Map, MapOptions
from maplibre.basemaps import Carto
from maplibre.sources import GeoJSONSource
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_maplibre

STATES = requests.get(
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
).json()
RAMPS = {
    "Sequential (orange-red)": ["interpolate", ["linear"], ["get", "density"], 0, "#ffffb2", 200, "#fd8d3c", 1000, "#bd0026"],
    "Diverging (blue-red)": ["interpolate", ["linear"], ["get", "density"], 0, "#2166ac", 200, "#f7f7f7", 1000, "#b2182b"],
}  # fmt: skip

ui.page_opts(fillable=True)
ui.input_select("ramp", "Color ramp", list(RAMPS))
ui.input_slider("min_density", "Minimum density shown", 0, 500, 0, step=25)

with ui.card(full_screen=True):

    @render_maplibre
    def choropleth():
        # Read once: the slider and dropdown restyle the existing map below,
        # so this function never needs to run again as the user adjusts them --
        # which also means the camera (pan/zoom) is never reset.
        with reactive.isolate():
            ramp = RAMPS[input.ramp()]
        m = Map(MapOptions(style=Carto.POSITRON, center=(-98.5, 39.8), zoom=3.3))
        m.add_source("states", GeoJSONSource(data=STATES))
        m.add_layer(
            Layer(id="states-fill", type=LayerType.FILL, source="states", paint={"fill-color": ramp})
        )
        return m


@reactive.effect
def _recolor():
    choropleth.widget.set_paint_property("states-fill", "fill-color", RAMPS[input.ramp()])


@reactive.effect
def _refilter():
    choropleth.widget.set_filter("states-fill", [">=", ["get", "density"], input.min_density()])
