from __future__ import annotations

import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_jscatter

app_ui = ui.page_fillable(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("selected"),
    ui.layout_columns(
        ui.card(ui.card_header("fill"), output_widget("fill_scatter")),
        ui.card(ui.card_header("fixed"), output_widget("fixed_scatter")),
    ),
)

POINTS = pd.DataFrame(
    {"x": np.linspace(0, 1, 40), "y": np.sin(np.linspace(0, 6, 40)) * 0.5 + 0.5}
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

    @render_jscatter
    def fill_scatter():
        counter.get()
        return Scatter(data=POINTS, x="x", y="y")

    @render_jscatter
    def fixed_scatter():
        return Scatter(data=POINTS, x="x", y="y", height=180)

    @render.text
    def selected():
        return str(len(reactive_read(fill_scatter.widget, "selection")))


app = App(app_ui, server)
