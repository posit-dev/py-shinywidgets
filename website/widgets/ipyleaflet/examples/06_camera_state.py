import ipyleaflet as L
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Camera accessors", fillable=True)

with ui.sidebar():
    ui.input_slider("zoom", "Zoom", value=12, min=4, max=18)

with ui.card():

    @render_ipyleaflet
    def map():
        return L.Map(center=(40.73, -73.99), zoom=12)


@reactive.effect
def _slider_to_map():
    map.widget.zoom = input.zoom()


@reactive.effect
def _map_to_slider():
    # zoom() also fires when Python sets .zoom (the line above), but the
    # slider ignores an update to the value it already holds, so this
    # doesn't loop
    ui.update_slider("zoom", value=map.zoom())


with ui.card(fill=False):

    @render.code
    def status():
        b = map.bounds()  # cancels (no output) until the browser first reports it
        return (
            f"zoom:   {map.zoom()}\n"
            f"center: {[round(c, 3) for c in map.center()]}\n"
            f"bounds: south={b[0][0]:.3f} west={b[0][1]:.3f} "
            f"north={b[1][0]:.3f} east={b[1][1]:.3f}"
        )
