# template: local raster viewer (~65 lines)
# A clean starting point for any local GeoTIFF/COG: band + colormap + value-range
# controls that restyle in place, plus click-to-sample using ipyleaflet's
# clicked() accessor.
# Run:  uv run --with 'localtileserver>=1.0.0' python -m shiny run gallery_template_raster_viewer.py
# Data: localtileserver.examples.get_bahamas() -- swap in your own
# TileClient(path_or_url) for a real dataset.
import ipyleaflet as L
from localtileserver import TileClient, examples, get_leaflet_tile_layer
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Raster viewer", fillable=True)

# Create the TileClient at module scope, never inside a render
client: TileClient = examples.get_bahamas()
COLORMAPS = ["greys", "viridis", "magma", "terrain"]

with ui.sidebar():
    ui.input_select("band", "Band", ["1", "2", "3"])
    ui.input_select("colormap", "Colormap", COLORMAPS)
    ui.input_slider("range", "Value range", 0, 255, value=[0, 255])

    @render.ui
    def clicked_value():
        c = map.clicked()
        if c is None:
            return "Click the map to sample a pixel."
        lat, lng = c["coordinates"]
        value = client.point(lng, lat).array[int(input.band()) - 1]
        return f"band {input.band()} = {int(value)} at {lat:.4f}, {lng:.4f}"


with ui.card():

    @render_ipyleaflet
    def map():
        m = L.Map(center=client.center(), zoom=11)
        m.add(get_leaflet_tile_layer(client, indexes=[1]))
        return m


@reactive.effect
def _restyle():
    # shinywidgets routes this through the loopback proxy automatically, so
    # restyling works the same locally and deployed -- see the guide's
    # "Behind a path prefix" section.
    map.widget.layers[1].url = client.get_tile_url(
        indexes=[int(input.band())],
        colormap=input.colormap(),
        vmin=input.range()[0],
        vmax=input.range()[1],
        client=True,
    )
