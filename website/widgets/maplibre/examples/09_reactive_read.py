import json

from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny.express import render, ui
from shinywidgets import render_maplibre

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_maplibre
        def city():
            return Map(MapOptions(style=Carto.DARK_MATTER, center=(2.3522, 48.8566), zoom=11))

    with ui.card():
        ui.card_header("Map state (accessors)")

        @render.code
        def state():
            vs = city.view_state()
            clicked = city.clicked()
            return (
                f"view_state:\n{json.dumps(vs, indent=2)}\n\n"
                f"clicked:\n{json.dumps(clicked) if clicked else '(nothing clicked yet)'}"
            )
