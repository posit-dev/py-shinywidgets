import ipyleaflet as L
from shiny import reactive, render, req
from shiny.express import input, ui

from shinywidgets import reactive_read, render_widget

ui.page_opts(title="ipyleaflet demo")

with ui.sidebar():
    ui.input_slider("zoom", "Map zoom level", value=4, min=1, max=10)

@render_widget
def lmap():
    return L.Map(center=(52, 360), zoom=4)

# When the slider changes, update the map's zoom attribute
@reactive.Effect
def _():
    lmap.widget.zoom = input.zoom()

# When zooming directly on the map, update the slider's value
@reactive.Effect
def _():
    zoom = reactive_read(lmap.widget, "zoom")
    ui.update_slider("zoom", value=zoom)


with ui.card(fill=False):
    # Everytime the map's bounds change, update the output message
    @render.ui
    def map_bounds():
        b = reactive_read(lmap.widget, "bounds")
        req(b)
        lat = [round(x) for x in [b[0][0], b[0][1]]]
        lon = [round(x) for x in [b[1][0], b[1][1]]]
        return f"The map bounds is currently {lat} / {lon}"
