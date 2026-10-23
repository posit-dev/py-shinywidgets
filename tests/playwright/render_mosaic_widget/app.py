from __future__ import annotations

import numpy as np
import pandas as pd
from mosaic_widget import MosaicWidget
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_mosaic_widget

rng = np.random.default_rng(0)
DATA = pd.DataFrame({"x": rng.normal(size=500), "y": rng.normal(size=500)})

SPEC = {
    "params": {"brush": {"select": "crossfilter"}},
    "vconcat": [
        {
            "plot": [
                {
                    "mark": "dot",
                    "data": {"from": "pts", "filterBy": "$brush"},
                    "x": "x",
                    "y": "y",
                },
                {"select": "intervalXY", "as": "$brush"},
            ],
            "width": 400,
            "height": 200,
        },
        {
            "plot": [
                {
                    "mark": "rectY",
                    "data": {"from": "pts", "filterBy": "$brush"},
                    "x": {"bin": "x"},
                    "y": {"count": ""},
                }
            ],
            "width": 400,
            "height": 150,
        },
    ],
}

app_ui = ui.page_fillable(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("selected_rows"),
    ui.layout_columns(
        ui.card(output_widget("mosaic"), style="height: 500px"),
        ui.card(output_widget("mosaic_fixed", height="260px")),
        fill=False,
    ),
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

    @render_mosaic_widget
    def mosaic():
        counter.get()
        return MosaicWidget(SPEC, data={"pts": DATA})

    @render_mosaic_widget
    def mosaic_fixed():
        return MosaicWidget(SPEC, data={"pts": DATA})

    @render.text
    def selected_rows():
        reactive_read(mosaic.widget, "params")
        return str(len(mosaic.widget.data().df()))


app = App(app_ui, server)
