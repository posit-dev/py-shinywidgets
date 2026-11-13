from __future__ import annotations

from geolibre import Map
from shiny.express import ui

from shinywidgets import render_geolibre

ui.page_opts(title="GeoLibre quickstart", fillable=True)

US_STATES = (
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/"
    "master/data/geojson/us-states.json"
)

with ui.card(full_screen=True):
    ui.card_header("The full GeoLibre app, as a Shiny output")

    @render_geolibre
    def map():
        m = Map(center=(-98.5, 39.8), zoom=4)
        m.add_geojson(US_STATES, name="US States", fillColor="#2a6fdb", fillOpacity=0.25)
        return m
