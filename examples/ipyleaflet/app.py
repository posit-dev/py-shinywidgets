import ipyleaflet as L
from shiny import App, reactive, render, req, ui

from shinywidgets import output_widget, reactive_read, render_widget

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_slider("zoom", "Map zoom level", value=4, min=1, max=10),
    ),
    ui.card(
        ui.output_text("map_bounds"),
        fill=False
    ),
    ui.card(
        output_widget("lmap")
    ),
    title="ipyleaflet demo"
)


def server(input, output, session):

    @output
    @render_widget
    def lmap():
        return L.Map(center=(52, 360), zoom=4)

    # When the slider changes, update the map's zoom attribute (2)
    @reactive.Effect
    def _():
        lmap.widget.zoom = input.zoom()

    # When zooming directly on the map, update the slider's value (2 and 3)
    @reactive.Effect
    def _():
        zoom = reactive_read(lmap.widget, "zoom")
        ui.update_slider("zoom", value=zoom)

    # Everytime the map's bounds change, update the output message (3)
    @output
    @render.text
    def map_bounds():
        b = reactive_read(lmap.widget, "bounds")
        req(b)
        lat = [round(x) for x in [b[0][0], b[0][1]]]
        lon = [round(x) for x in [b[1][0], b[1][1]]]
        return f"The map bounds is currently {lat} / {lon}"


app = App(app_ui, server)
