import ipyleaflet as L
from htmltools import css
from shiny import *

from shinywidgets import output_widget, reactive_read, register_widget

app_ui = ui.page_fillable(
    ui.div(
        ui.input_slider("zoom", "Map zoom level", value=4, min=1, max=10),
        ui.output_text("map_bounds"),
        style=css(
            display="flex", justify_content="center", align_items="center", gap="2rem"
        ),
    ),
    output_widget("map"),
)


def server(input, output, session):

    # Initialize and display when the session starts (1)
    map = L.Map(center=(52, 360), zoom=4)
    register_widget("map", map)

    # When the slider changes, update the map's zoom attribute (2)
    @reactive.Effect
    def _():
        map.zoom = input.zoom()

    # When zooming directly on the map, update the slider's value (2 and 3)
    @reactive.Effect
    def _():
        ui.update_slider("zoom", value=reactive_read(map, "zoom"))

    # Everytime the map's bounds change, update the output message (3)
    @output
    @render.text
    def map_bounds():
        b = reactive_read(map, "bounds")
        req(b)
        lat = [b[0][0], b[0][1]]
        lon = [b[1][0], b[1][1]]
        return f"The current latitude is {lat} and longitude is {lon}"


app = App(app_ui, server)
