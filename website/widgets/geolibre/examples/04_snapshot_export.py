from __future__ import annotations

from geolibre import Map
from shiny import render
from shiny.express import ui

from shinywidgets import render_geolibre

ui.page_opts(title="Snapshot export", fillable=True)

US_STATES = (
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/"
    "master/data/geojson/us-states.json"
)

with ui.layout_columns(col_widths=[9, 3]):
    with ui.card(full_screen=True):

        @render_geolibre
        def map():
            m = Map(center=(-98.5, 39.8), zoom=4)
            m.add_geojson(US_STATES, name="US States", fillColor="#2a6fdb", fillOpacity=0.25)
            return m

    with ui.card():
        ui.card_header("Export")

        # to_image_async() awaits the app's reply, so it runs directly on
        # Shiny's event loop -- a download handler isn't part of the
        # reactive flush, so (unlike a reactive.effect) awaiting it here
        # doesn't block the reply from being delivered.
        @render.download_button(filename="map.png", label="Download PNG")
        async def snapshot():
            yield await map.widget.to_image_async()
