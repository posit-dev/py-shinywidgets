import ipyleaflet as L
from shiny.express import ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Split map comparison", fillable=True)

with ui.card():

    @render_ipyleaflet
    def map():
        m = L.Map(center=(40.73, -73.99), zoom=12)
        left = L.basemap_to_tiles(L.basemaps.OpenStreetMap.Mapnik)
        right = L.basemap_to_tiles(L.basemaps.Esri.WorldImagery)
        m.add(L.SplitMapControl(left_layer=left, right_layer=right))
        return m
