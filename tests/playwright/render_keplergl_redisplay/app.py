from __future__ import annotations

import pandas as pd
from keplergl import KeplerGl
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_keplergl, session_lifetime

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.card(output_widget("cached_map"), height="500px", id="cached_card"),
    ui.card(output_widget("swapped_map"), height="500px", id="swapped_card"),
)

POINTS = pd.DataFrame(
    {"lat": [37.77, 37.80, 37.75], "lon": [-122.42, -122.27, -122.40], "n": [1, 2, 3]}
)


def server(input, output, session):
    counter = reactive.value(0)
    cached: list[KeplerGl] = []

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    # The same widget instance is displayed on every render
    @render_keplergl
    def cached_map():
        counter.get()
        if not cached:
            with session_lifetime():
                cached.append(KeplerGl(data={"data": POINTS}))
        return cached[0]

    # Auto-sized on the first render, then a widget with its own height
    @render_keplergl
    def swapped_map():
        if counter.get() == 0:
            return POINTS
        return KeplerGl(data={"data": POINTS}, height=250)


app = App(app_ui, server)
