# Bundled real RGB imagery (no network needed): a 1999 aerial survey of
# Exuma, Bahamas, shipped inside the localtileserver package itself.
import ipyleaflet as L
from localtileserver import TileClient, examples, get_leaflet_tile_layer
from shiny.express import ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="localtileserver quickstart", fillable=True)

# Create the TileClient at module scope, never inside a render: the first
# open takes a few seconds, later layers on the same server are fast.
client: TileClient = examples.get_bahamas()

with ui.card():

    @render_ipyleaflet
    def map():
        m = L.Map(center=client.center(), zoom=9)
        m.add(get_leaflet_tile_layer(client))
        return m
