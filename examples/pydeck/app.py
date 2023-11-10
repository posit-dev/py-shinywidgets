import pydeck as pdk
from shiny import *

from shinywidgets import *

app_ui = ui.page_fillable(
    ui.input_slider("zoom", "Zoom", 0, 20, 6, step=1),
    output_widget("pydeck")
)

def server(input: Inputs, output: Outputs, session: Session):

    UK_ACCIDENTS_DATA = "https://raw.githubusercontent.com/visgl/deck.gl-data/master/examples/3d-heatmap/heatmap-data.csv"

    layer = pdk.Layer(
        "HexagonLayer",  # `type` positional argument is here
        UK_ACCIDENTS_DATA,
        get_position=["lng", "lat"],
        auto_highlight=True,
        elevation_scale=50,
        pickable=True,
        elevation_range=[0, 3000],
        extruded=True,
        coverage=1,
    )

    view_state = pdk.ViewState(
        longitude=-1.415,
        latitude=52.2323,
        zoom=6,
        min_zoom=5,
        max_zoom=15,
        pitch=40.5,
        bearing=-27.36,
    )

    deck = pdk.Deck(layers=[layer], initial_view_state=view_state)

    # Register either the deck (or deck_widget) instance
    register_widget("pydeck", deck)

    @reactive.Effect()
    def _():
        deck.initial_view_state.zoom = input.zoom()
        deck.update()


app = App(app_ui, server)
