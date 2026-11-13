from __future__ import annotations

from geolibre import Map
from shiny.express import ui

from shinywidgets import render_geolibre

ui.page_opts(title="Layout and sizing", fillable=True)

with ui.layout_columns(col_widths=[4, 4, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Default: fills the card")

        @render_geolibre
        def fills():
            return Map(center=(-98.5, 39.8), zoom=3)

    with ui.card(full_screen=True):
        ui.card_header('Map(height="300px"): opts out of filling')

        @render_geolibre
        def fixed():
            return Map(center=(-98.5, 39.8), zoom=3, height="300px")

    with ui.card(full_screen=True):
        ui.card_header('render_geolibre(height="250px"): sizes a default-height map')

        @render_geolibre(height="250px")
        def sized():
            return Map(center=(-98.5, 39.8), zoom=3)
