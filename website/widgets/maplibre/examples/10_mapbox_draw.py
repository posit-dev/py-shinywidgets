from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny.express import render, ui
from shinywidgets import render_maplibre

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_maplibre
        def city():
            m = Map(MapOptions(style=Carto.POSITRON, center=(2.3522, 48.8566), zoom=11))
            m.add_mapbox_draw()
            return m

    with ui.card():
        ui.card_header("Drawn features")

        @render.code
        def drawn():
            feats = city.drawn_features()
            return f"{len(feats)} feature(s) drawn\n\n{feats}"
