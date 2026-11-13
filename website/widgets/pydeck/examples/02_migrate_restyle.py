import pydeck as pdk
import requests
from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_maplibre

BIKE_RACKS = requests.get(
    "https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-bike-parking.json"
).json()
TOOLTIP = {"bike-racks": "{{ADDRESS}}: {{SPACES}} spaces"}

ui.page_opts(fillable=True)
ui.input_slider("radius_scale", "Radius scale", 1, 20, 6)

with ui.card(full_screen=True):

    @render_maplibre
    def bike_racks():
        m = Map(MapOptions(style=Carto.POSITRON, center=(-122.4194, 37.7749), zoom=12))
        # An empty overlay: the effect below fills it, so the data crosses the
        # wire once (calls made before the map renders are queued), not twice.
        m.add_deck_layers([], tooltip=TOOLTIP)
        return m


@reactive.effect
def _restyle():
    # set_deck_layers() restyles in place: the camera stays put, and (unlike a
    # pydeck Deck.update(), which raises on pydeck >= 0.9) this actually works.
    bike_racks.widget.set_deck_layers([scatter_layer()], tooltip=TOOLTIP)


def scatter_layer() -> pdk.Layer:
    return pdk.Layer(
        "ScatterplotLayer",
        BIKE_RACKS,
        id="bike-racks",
        get_position="COORDINATES",
        get_radius="SPACES",
        get_fill_color=[255, 140, 0],
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_scale=input.radius_scale(),
        radius_min_pixels=1,
        radius_max_pixels=100,
        line_width_min_pixels=1,
    )
