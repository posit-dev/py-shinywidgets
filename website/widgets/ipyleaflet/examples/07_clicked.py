import ipyleaflet as L
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Map clicks", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card():

        @render_ipyleaflet
        def map():
            return L.Map(center=(40.73, -73.99), zoom=13)

    with ui.card():
        ui.card_header("map.clicked()")

        @render.code
        def click():
            c = map.clicked()
            if c is None:
                return "Click the map to see its coordinates."
            lat, lng = c["coordinates"]
            return f"lat={lat:.4f}\nlng={lng:.4f}"
