from __future__ import annotations

from geolibre import Map
from shiny import reactive
from shiny.express import input, ui

from shinywidgets import render_geolibre

ui.page_opts(title="Drive the map from an input", fillable=True)

CITIES = {
    "New York": (-74.0, 40.7),
    "San Francisco": (-122.4, 37.8),
    "Chicago": (-87.6, 41.9),
}

with ui.sidebar():
    ui.input_select("city", "Jump to a city", list(CITIES))

with ui.card(full_screen=True):

    @render_geolibre
    def map():
        return Map(center=(-98.5, 39.8), zoom=4)


# set_center() mutates the project trait and syncs to the browser -- no
# re-render, so zoom, added layers, and styling are untouched.
@reactive.effect
def _():
    lng, lat = CITIES[input.city()]
    map.widget.set_center(lng, lat, zoom=9)
