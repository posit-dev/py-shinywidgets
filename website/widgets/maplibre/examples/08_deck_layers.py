import pydeck as pdk
import requests
from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_maplibre

EARTHQUAKES = requests.get(
    "https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson"
).json()
POINTS = [f["geometry"]["coordinates"][:2] for f in EARTHQUAKES["features"]]

ui.page_opts(fillable=True)
ui.input_slider("radius", "Hexagon radius (km)", 50, 500, 200, step=50)

with ui.card(full_screen=True):

    @render_maplibre
    def deck():
        m = Map(MapOptions(style=Carto.DARK_MATTER, center=(0, 20), zoom=1.2))
        # pydeck.Layer objects pass straight to a maplibre Map -- this is the
        # migration path for @render_pydeck, which pydeck 0.9 removed support for.
        m.add_deck_layers([hexagon_layer()])
        return m


@reactive.effect
def _restyle():
    # set_deck_layers() restyles in place: the camera position is kept, and the
    # 6,100 points aren't re-sent (only the layer's style properties are).
    deck.widget.set_deck_layers([hexagon_layer()])


def hexagon_layer() -> pdk.Layer:
    return pdk.Layer(
        "HexagonLayer",
        POINTS,
        id="quakes-hex",
        get_position="-",
        radius=input.radius() * 1000,
        extruded=True,
        elevation_scale=2000,
        pickable=True,
    )
