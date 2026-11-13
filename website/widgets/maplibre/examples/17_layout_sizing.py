from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny.express import ui
from shinywidgets import render_maplibre

ui.page_opts(fillable=True)

with ui.layout_columns(height="400px"):
    with ui.card(full_screen=True):
        ui.card_header("No explicit height: fills the card")

        @render_maplibre
        def fills():
            return Map(MapOptions(style=Carto.POSITRON, center=(2.3522, 48.8566), zoom=10))

    with ui.card():
        ui.card_header("height=\"150px\": fixed, doesn't grow")

        @render_maplibre(height="150px")
        def fixed():
            return Map(MapOptions(style=Carto.POSITRON, center=(2.3522, 48.8566), zoom=10))
