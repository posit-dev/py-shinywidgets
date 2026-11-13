import ipyleaflet as L
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Overview map stays in sync", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card():

        @render_ipyleaflet
        def main():
            return L.Map(center=(40.73, -73.99), zoom=14)

    with ui.card():

        @render_ipyleaflet
        def overview():
            m = L.Map(center=(40.73, -73.99), zoom=10)
            m.add(L.Rectangle(bounds=((40.72, -74.0), (40.74, -73.98)), name="extent"))
            return m


# The overview map never re-renders: panning or zooming the main map just
# moves its center and resizes its rectangle, so the overview keeps its own
# zoom level and any layers a user added to it.
@reactive.effect
def _sync_overview_center():
    overview.widget.center = main.center()


@reactive.effect
def _sync_extent_rectangle():
    extent = next(lyr for lyr in overview.widget.layers if lyr.name == "extent")
    extent.bounds = main.bounds()
