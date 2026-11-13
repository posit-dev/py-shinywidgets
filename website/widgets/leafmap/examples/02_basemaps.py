import leafmap
from shiny.express import input, ui
from shinywidgets import render_leafmap

ui.page_opts(title="leafmap basemaps", fillable=True)

with ui.sidebar():
    # leafmap.basemaps has 100+ names from the xyzservices registry (Esri,
    # CartoDB, USGS, NASA GIBS, ...) -- add_basemap() looks one up by name
    ui.input_select(
        "basemap",
        "Basemap",
        [
            "Esri.WorldImagery",
            "OpenTopoMap",
            "Stadia.AlidadeSmoothDark",
            "USGS.USImageryTopo",
        ],
    )


@render_leafmap
def map():
    m = leafmap.Map(center=(36.1, -112.1), zoom=10)  # Grand Canyon
    m.add_basemap(input.basemap())
    return m
