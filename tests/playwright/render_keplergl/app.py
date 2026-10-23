from __future__ import annotations

import pandas as pd
from keplergl import KeplerGl
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_keplergl

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.card(output_widget("map"), height="500px", id="fill_card"),
    output_widget("fixed_map", height="300px"),
    output_widget("tall_map"),
    output_widget("missing_values_map", height="300px"),
    ui.output_text("missing_values_layers"),
    ui.output_text("n_layers"),
    ui.output_text("map_height"),
)

POINTS = pd.DataFrame(
    {
        "lat": [37.77, 37.80, 37.75, 37.79],
        "lon": [-122.42, -122.27, -122.40, -122.41],
        "n": [1, 2, 3, 4],
    }
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

    @render_keplergl
    def map():
        counter.get()
        return POINTS

    @render_keplergl
    def fixed_map():
        return POINTS

    @render_keplergl
    def tall_map():
        return KeplerGl(data={"data": POINTS}, height=250)

    @render_keplergl
    def missing_values_map():
        return POINTS.assign(n=[1, None, 3, 4])

    @render.text
    def n_layers():
        return f"layers: {count_layers(map.widget)}"

    @render.text
    def missing_values_layers():
        return f"layers: {count_layers(missing_values_map.widget)}"

    @render.text
    def map_height():
        return f"height: {reactive_read(map.widget, 'height')}"


def count_layers(widget: KeplerGl | None) -> int:
    config = reactive_read(widget, "config")
    return len(config.get("config", {}).get("visState", {}).get("layers", []))


app = App(app_ui, server)
