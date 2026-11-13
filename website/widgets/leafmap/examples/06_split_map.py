import leafmap
from shiny.express import ui
from shinywidgets import render_leafmap

ui.page_opts(title="leafmap split map", fillable=True)


@render_leafmap
def map():
    m = leafmap.Map(center=(37.75, -119.58), zoom=11)  # Yosemite Valley
    # split_map() divides the existing map into two synced panes with a
    # draggable divider -- handy for before/after imagery or basemap compares
    m.split_map(
        left_layer="Esri.WorldImagery",
        right_layer="USGS.USTopo",
        left_label="Satellite",
        right_label="USGS Topo",
    )
    return m
