from __future__ import annotations

from maplibre import Map
from shiny.express import ui
from shinywidgets import render_maplibre

ui.h2("Express output with an explicit height")


@render_maplibre(height="250px")
def map():
    return Map()
