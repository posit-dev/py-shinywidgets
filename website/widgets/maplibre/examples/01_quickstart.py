from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny.express import ui
from shinywidgets import render_maplibre

ui.page_opts(fillable=True)

with ui.card(full_screen=True):

    @render_maplibre
    def city():
        return Map(
            MapOptions(style=Carto.DARK_MATTER, center=(2.3522, 48.8566), zoom=11)
        )
