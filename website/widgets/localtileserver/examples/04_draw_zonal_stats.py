# Bundled real RGB imagery (no network needed): a 1999 aerial survey of
# Exuma, Bahamas, shipped inside the localtileserver package itself.
import io

import ipyleaflet as L
import numpy as np
import plotly.express as px
from localtileserver import TileClient, examples, get_leaflet_tile_layer
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet, render_plotly

ui.page_opts(title="Draw a region, compute zonal stats", fillable=True)

client: TileClient = examples.get_bahamas()

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card():

        @render_ipyleaflet
        def map():
            m = L.Map(center=client.center(), zoom=11)
            m.add(get_leaflet_tile_layer(client))
            m.add(L.DrawControl(rectangle={"shapeOptions": {}}, polygon={}, circle={}, polyline={}, marker={}))
            return m

    with ui.card(full_screen=True):
        ui.card_header("Band 1 (red) histogram inside the drawn shape")

        @render_plotly
        def hist():
            feats = map.drawn_features()  # [] until something is drawn
            if not feats:
                return px.histogram()
            # client.feature() takes GeoJSON straight from drawn_features() --
            # no CRS conversion needed, unlike client.part()'s bbox (see Gotchas)
            raw = client.feature(feats[-1]["geometry"], indexes=[1], encoding="npy")
            band, mask = np.load(io.BytesIO(raw))
            values = band[mask > 0]  # drop pixels outside the (non-rectangular) shape
            return px.histogram(values, nbins=40, labels={"value": "pixel value (band 1)"})
