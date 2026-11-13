import ipyleaflet as L
from shiny import req
from shiny.express import render, ui
from shinywidgets import reactive_read, render_ipyleaflet

ui.page_opts(title="Draggable marker (reactive_read)", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card():

        @render_ipyleaflet
        def map():
            m = L.Map(center=(40.73, -73.99), zoom=14)
            m.add(L.Marker(location=(40.73, -73.99), draggable=True, name="me"))
            return m

    with ui.card():
        ui.card_header("Drag the marker")

        @render.code
        def location():
            req(map.widget)
            marker = next(lyr for lyr in map.widget.layers if lyr.name == "me")
            lat, lng = reactive_read(marker, "location")
            return f"lat={lat:.4f}\nlng={lng:.4f}"
