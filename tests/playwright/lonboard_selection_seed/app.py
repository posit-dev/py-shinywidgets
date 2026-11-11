from __future__ import annotations

import geoarrow.rust.core as gr
import numpy as np
from arro3.core import Table
from lonboard import Map, ScatterplotLayer
from lonboard.view_state import MapViewState
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_lonboard

# The accessor read the test asserts on is gated behind an action button, and
# NOTHING reads it at startup, so the pick below lands before the accessor's
# first read. The accessor attaches at render, so the pick must be reflected
# in that late first read (see the test).

# Five points in a tight cluster around (20, 40), so a center click picks one.
coords = (20 + np.linspace(-0.02, 0.02, 5), 40 + np.linspace(-0.02, 0.02, 5))
table = Table.from_arrays([gr.points(coords, crs="EPSG:4326")], names=["geometry"])

app_ui = ui.page_fillable(
    ui.input_action_button("read_pick", "Read pick"),
    ui.output_text("picked"),
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
    @reactive.event(input.read_pick)
    def picked():
        return str(map.selected_index())


app = App(app_ui, server)
