from __future__ import annotations

from geolibre import Map
from shiny.express import ui

from shinywidgets import render_geolibre

ui.page_opts(title="Toolset + legend", fillable=True)

CITIES = [
    ("New York", -74.0, 40.7),
    ("Los Angeles", -118.2, 34.0),
    ("Chicago", -87.6, 41.9),
    ("Houston", -95.4, 29.8),
    ("Phoenix", -112.1, 33.4),
]

with ui.card(full_screen=True):
    ui.card_header("A legend and the built-in measuring tool, with no custom UI code")

    @render_geolibre
    def map():
        m = Map(center=(-98.5, 39.8), zoom=3.5)
        m.add_circle_markers(
            [(lng, lat) for _, lng, lat in CITIES],
            name="Major cities",
            radius=10,
            fillColor="#e3342f",
        )
        m.add_legend("Cities", legend_dict={"Population > 1M": "#e3342f"})
        m.show_control("measure", collapsed=False, distance_unit="miles")
        return m
