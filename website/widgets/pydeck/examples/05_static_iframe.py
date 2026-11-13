import pydeck as pdk
import requests
from shiny.express import render, ui

BIKE_RACKS = requests.get(
    "https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-bike-parking.json"
).json()

ui.page_opts(fillable=True)

with ui.card(full_screen=True):

    @render.ui
    def bike_racks():
        layer = pdk.Layer(
            "ScatterplotLayer",
            BIKE_RACKS,
            get_position="COORDINATES",
            get_radius="SPACES",
            get_fill_color=[255, 140, 0],
            radius_scale=6,
            radius_min_pixels=1,
        )
        view_state = pdk.ViewState(latitude=37.7749, longitude=-122.4194, zoom=12)
        deck = pdk.Deck(layers=[layer], initial_view_state=view_state)
        # deck.to_html() with no filename returns None -- only as_string=True
        # gives you the HTML to embed. There's no reactivity here: every input
        # change re-renders this whole function and re-sends the full page.
        return ui.tags.iframe(
            srcdoc=deck.to_html(as_string=True),
            style="border:0;width:100%;height:100%;flex:1 1 auto",
        )
