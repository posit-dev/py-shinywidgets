import ipyleaflet as L
from shiny.express import ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="bundle: ipyleaflet", fillable=True)


@render_ipyleaflet
def map():
    return L.Map(center=(45.5, -122.6), zoom=10)
