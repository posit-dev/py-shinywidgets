# showcase: raster explorer (~110 lines)
# A single localtileserver raster, three ways to read it: restyle the band,
# colormap, and value range in place; click for the exact pixel value at a
# point; and draw a rectangle for a histogram of everything inside it.
# Run:  uv run --with 'localtileserver>=1.0.0' python -m shiny run gallery_showcase_elevation_explorer.py
# Data: localtileserver.examples.get_bahamas() -- a bundled 1999 aerial RGB
# survey of Exuma, Bahamas, shipped inside the localtileserver package itself
# (no network needed).
import io

import ipyleaflet as L
import numpy as np
import plotly.express as px
from localtileserver import TileClient, examples, get_leaflet_tile_layer
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyleaflet, render_plotly

ui.page_opts(title="Raster explorer", fillable=True)

client: TileClient = examples.get_bahamas()
BANDS = {"Red (b1)": [1], "Green (b2)": [2], "Blue (b3)": [3], "True color": [1, 2, 3]}
COLORMAPS = ["greys", "viridis", "magma", "terrain"]

with ui.layout_columns(col_widths=[8, 4, 4, 4]):
    with ui.card():
        ui.card_header("Click to sample, draw to summarize")

        @render_ipyleaflet
        def map():
            m = L.Map(center=client.center(), zoom=11)
            m.add(get_leaflet_tile_layer(client, indexes=[1, 2, 3]))
            m.add(L.DrawControl(rectangle={"shapeOptions": {}}, polygon={}, circle={}, polyline={}, marker={}))
            return m

    with ui.card():
        ui.card_header("Restyle (in place -- no re-render)")
        ui.input_select("band", "Band", list(BANDS), selected="True color")
        ui.input_select("colormap", "Colormap (single band)", COLORMAPS)
        ui.input_slider("range", "Value range", 0, 255, value=[0, 255])

    with ui.card():
        ui.card_header("Click a point")

        @render.ui
        def pixel():
            c = map.clicked()
            if c is None:
                return "Click the map."
            lat, lng = c["coordinates"]
            value = [int(v) for v in client.point(lng, lat).array]
            return ui.div(ui.h5(str(value)), f"{lat:.4f}, {lng:.4f}")

    with ui.card():
        ui.card_header("Drawn region")

        @render.ui
        def summary():
            feats = map.drawn_features()
            if not feats:
                return "Draw a rectangle."
            band, mask = _window(feats[-1])
            values = band[mask > 0]
            return ui.div(
                ui.h5(f"{values.mean():.0f} avg"),
                f"{values.min()}-{values.max()} range, {values.size} px",
            )


@reactive.effect
def _restyle():
    indexes = BANDS[input.band()]
    kwargs = {} if len(indexes) > 1 else {"colormap": input.colormap()}
    map.widget.layers[1].url = client.get_tile_url(
        indexes=indexes, vmin=input.range()[0], vmax=input.range()[1], client=True, **kwargs
    )


def _window(feature: dict) -> tuple:
    # client.feature() takes GeoJSON straight from drawn_features() -- no CRS
    # conversion needed, unlike client.part()'s bbox (see guide Gotchas)
    raw = client.feature(feature["geometry"], indexes=[1], encoding="npy")
    return np.load(io.BytesIO(raw))


with ui.card(full_screen=True):
    ui.card_header("Band 1 histogram inside the drawn region")

    @render_plotly
    def hist():
        feats = map.drawn_features()
        if not feats:
            return px.histogram()
        band, mask = _window(feats[-1])
        values = band[mask > 0]
        return px.histogram(values, nbins=40, labels={"value": "pixel value (band 1)"})
