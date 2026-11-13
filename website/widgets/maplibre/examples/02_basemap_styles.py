from maplibre import Map, MapOptions
from maplibre.basemaps import Basemap, Carto, OpenFreeMap
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_maplibre

STYLES = {
    "Carto Dark Matter": Basemap.carto_url(Carto.DARK_MATTER),
    "Carto Positron": Basemap.carto_url(Carto.POSITRON),
    "OpenFreeMap Liberty": Basemap.openfreemap_url(OpenFreeMap.LIBERTY),
}

ui.page_opts(fillable=True)
ui.input_radio_buttons("style", "Basemap style", list(STYLES), inline=True)

with ui.card(full_screen=True):

    @render_maplibre
    def city():
        return Map(MapOptions(style=STYLES["Carto Dark Matter"], center=(2.3522, 48.8566), zoom=11))


@reactive.effect
def _set_style():
    # setStyle is a MapLibre GL JS method with no dedicated Python wrapper;
    # add_call() reaches it directly. It swaps the basemap without re-rendering
    # the widget, so the camera position is kept.
    city.widget.add_call("setStyle", STYLES[input.style()])
