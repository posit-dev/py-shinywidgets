import ipywidgets
import ipyleaflet as L
from shiny.express import ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="ipyleaflet quickstart", fillable=True)

with ui.card():

    @render_ipyleaflet
    def map():
        m = L.Map(center=(40.73, -73.99), zoom=15)
        marker = L.Marker(location=(40.735, -73.991))
        marker.popup = ipywidgets.HTML("<b>Union Square</b><br>14th St &amp; Broadway")
        m.add(marker)
        return m
