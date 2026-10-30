from __future__ import annotations

import geoarrow.rust.core as gr
import numpy as np
from arro3.core import Table
from lonboard import Map, ScatterplotLayer
from lonboard.view_state import MapViewState
from shiny import App, render, ui
from shinywidgets import output_widget, render_lonboard

# Five points in a tight cluster around (20, 40), so a center click picks one.
# The distinct longitude/latitude magnitudes make a lat/lng swap fail loudly.
coords = (20 + np.linspace(-0.02, 0.02, 5), 40 + np.linspace(-0.02, 0.02, 5))
table = Table.from_arrays([gr.points(coords, crs="EPSG:4326")], names=["geometry"])

app_ui = ui.page_fillable(
    ui.output_text("view_state"),
    ui.output_text("picked"),
    ui.output_text("clicked"),
    ui.output_text("bbox"),
    output_widget("map"),
)


def server(input, output, session):
    @render_lonboard
    def map():
        return Map(
            ScatterplotLayer(table=table, radius_min_pixels=15),
            view_state=MapViewState(longitude=20, latitude=40, zoom=6),
        )

    @render.text
    def view_state():
        vs = map.view_state()
        return f"{vs.longitude:.2f},{vs.latitude:.2f},{vs.zoom:.2f}"

    @render.text
    def picked():
        return str(map.selected_index())

    @render.text
    def clicked():
        return str(map.clicked())

    @render.text
    def bbox():
        return str(map.selected_bounds())


app = App(app_ui, server)
