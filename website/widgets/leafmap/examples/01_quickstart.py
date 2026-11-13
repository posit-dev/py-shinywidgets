import leafmap
from shiny.express import ui
from shinywidgets import render_leafmap

ui.page_opts(title="leafmap quick start", fillable=True)


@render_leafmap
def map():
    m = leafmap.Map(center=(47.62, -122.33), zoom=11)
    m.add_basemap("Esri.WorldImagery")
    m.add_marker(location=(47.6062, -122.3321), tooltip="Seattle")
    return m
