# Public COG over the network: NAIP aerial imagery of San Francisco Bay,
# served from a public bucket via /vsicurl/ (first open takes a few seconds).
import ipyleaflet as L
from localtileserver import TileClient, examples, get_leaflet_tile_layer
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Restyle in place", fillable=True)

client: TileClient = examples.get_san_francisco()
BANDS = {"Red (b1)": [1], "Green (b2)": [2], "Blue (b3)": [3], "True color": [1, 2, 3]}
COLORMAPS = ["greys", "viridis", "magma", "terrain"]

render_count = reactive.value(0)

with ui.sidebar():
    ui.input_select("band", "Band", list(BANDS), selected="True color")
    ui.input_select("colormap", "Colormap (single band only)", COLORMAPS)
    ui.input_slider("range", "Value range (vmin/vmax)", 0, 255, value=[0, 255])

    @render.code
    def renders():
        return f"map() has rendered {render_count()} time(s)"

with ui.card():

    @render_ipyleaflet
    def map():
        with reactive.isolate():
            render_count.set(render_count() + 1)
        m = L.Map(center=client.center(), zoom=13)
        m.add(get_leaflet_tile_layer(client, indexes=[1, 2, 3]))
        return m


@reactive.effect
def _restyle():
    indexes = BANDS[input.band()]
    kwargs = {} if len(indexes) > 1 else {"colormap": input.colormap()}
    url = client.get_tile_url(
        indexes=indexes,
        vmin=input.range()[0],
        vmax=input.range()[1],
        client=True,
        **kwargs,
    )
    map.widget.layers[1].url = url
