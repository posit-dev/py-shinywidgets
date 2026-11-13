# Public COG over the network: a USGS 1m DEM of a slice of the Colorado
# Rockies, served from a public bucket via /vsicurl/.
import ipyleaflet as L
from localtileserver import TileClient, examples, get_leaflet_tile_layer
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Click to sample the raster", fillable=True)

client: TileClient = examples.get_co_elevation()
STATS = client.statistics()["b1"]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card():

        @render_ipyleaflet
        def map():
            m = L.Map(center=client.center(), zoom=14)
            m.add(get_leaflet_tile_layer(client, colormap="terrain", vmin=STATS["min"], vmax=STATS["max"]))
            return m

    with ui.card():
        ui.card_header("Elevation at your last click")

        @render.ui
        def elevation():
            c = map.clicked()
            if c is None:
                return "Click the map to sample the DEM there."
            lat, lng = c["coordinates"]
            # Sampled server-side, straight from the source raster -- not from
            # the (possibly rescaled/colormapped) tile the browser is showing
            value = client.point(lng, lat).array[0]
            return ui.div(
                ui.h5(f"{value:.0f} m"),
                f"at {lat:.4f}, {lng:.4f}",
            )
