from __future__ import annotations

import numpy as np
import pandas as pd
from pyobsplot import Plot
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_obsplot

rng = np.random.default_rng(0)
N = 300
DATA = pd.DataFrame(
    {
        "x": rng.normal(size=N),
        "y": rng.normal(size=N),
        "g": rng.choice(["a", "b"], size=N),
    }
)

app_ui = ui.page_fillable(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.input_action_button("recolor", "Recolor in place"),
    ui.card(output_widget("scatter"), id="scatter_card"),
    ui.card(output_widget("fixed", height="300px"), id="fixed_card"),
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

    @render_obsplot
    def scatter():
        counter.get()
        return Plot.plot(
            {
                "grid": True,
                "color": {"legend": True},
                "marks": [
                    Plot.dot(DATA, {"x": "x", "y": "y", "fill": "g", "tip": True}),
                ],
            }
        )

    @render_obsplot
    def fixed():
        return Plot.plot({"marks": [Plot.dot(DATA, {"x": "x", "y": "y"})]})

    @reactive.effect
    @reactive.event(input.recolor)
    def _():
        # In-place update: no re-render, just a new spec
        scatter.widget.spec = {
            "marks": [Plot.dot(DATA, {"x": "x", "y": "y", "fill": "red"})],
        }


app = App(app_ui, server)
