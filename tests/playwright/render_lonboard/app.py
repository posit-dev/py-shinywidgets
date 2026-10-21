from __future__ import annotations

import geoarrow.rust.core as gr
import numpy as np
from arro3.core import Table
from lonboard import Map, ScatterplotLayer
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_lonboard


def points(n: int = 1000) -> Table:
    rng = np.random.default_rng(0)
    coords = (rng.uniform(-100, -80, n), rng.uniform(30, 45, n))
    return Table.from_arrays([gr.points(coords, crs="EPSG:4326")], names=["geometry"])


app_ui = ui.page_fillable(
    ui.layout_columns(
        ui.card(output_widget("map")),
        ui.card(output_widget("map_fixed")),
        ui.card(output_widget("map_output_height", height="300px")),
    ),
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("view_state"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    # A GeoArrow table is converted to a Map via lonboard.viz()
    @render_lonboard
    def map():
        input.rerender()
        return points()

    @render_lonboard
    def map_fixed():
        return Map(ScatterplotLayer(table=points()), height=250)

    @render_lonboard
    def map_output_height():
        return ScatterplotLayer(table=points())

    @render.text
    def view_state():
        state = reactive_read(map.widget, "view_state")
        return f"longitude={state.longitude:.4f}" if state else "none"


app = App(app_ui, server)
