import pydeck as pdk
from shiny.express import ui
from shinywidgets import render_pydeck

ui.page_opts(fillable=True)

BIKE_RACKS = "https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-bike-parking.json"


with ui.card(full_screen=True):

    @render_pydeck
    def bike_racks():
        layer = pdk.Layer(
            "ScatterplotLayer",
            BIKE_RACKS,
            get_position="COORDINATES",
            get_radius="SPACES",
            get_fill_color=[255, 140, 0],
            pickable=True,
            radius_scale=6,
        )
        view_state = pdk.ViewState(
            latitude=37.7749, longitude=-122.4194, zoom=11
        )
        return pdk.Deck(layers=[layer], initial_view_state=view_state)
