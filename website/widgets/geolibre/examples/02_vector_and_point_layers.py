from __future__ import annotations

from geolibre import Map
from shiny.express import ui

from shinywidgets import render_geolibre

ui.page_opts(title="Vector + point layers", fillable=True)

US_STATES = (
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/"
    "master/data/geojson/us-states.json"
)

# name, lng, lat, population
CITIES = [
    ("New York", -74.0, 40.7, 8_478_000),
    ("Los Angeles", -118.2, 34.0, 3_878_000),
    ("Chicago", -87.6, 41.9, 2_721_000),
    ("Houston", -95.4, 29.8, 2_314_000),
    ("Phoenix", -112.1, 33.4, 1_650_000),
]

with ui.card(full_screen=True):
    ui.card_header("A polygon layer and a point layer, each its own entry in the panel")

    @render_geolibre
    def map():
        m = Map(center=(-98.5, 39.8), zoom=3.5)
        m.add_geojson(US_STATES, name="US States", fillColor="#cbd5e0", fillOpacity=0.25)
        m.add_circle_markers(
            [(lng, lat) for _, lng, lat, _ in CITIES],
            name="Largest cities",
            radius=10,
            fillColor="#e3342f",
        )
        return m
