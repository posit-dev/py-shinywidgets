from __future__ import annotations

import numpy as np
import pandas as pd
from mosaic_widget import MosaicWidget
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_mosaic_widget

rng = np.random.default_rng(1)
n = 2000
species = rng.choice(["Adelie", "Chinstrap", "Gentoo"], size=n)
offset = pd.Series(species).map({"Adelie": 0, "Chinstrap": 1, "Gentoo": 2}).to_numpy()
penguins = pd.DataFrame(
    {
        "species": species,
        "flipper_length": rng.normal(185 + 12 * offset, 6),
        "body_mass": rng.normal(3500 + 700 * offset, 250),
    }
)

# Every plot reads from the "penguins" table through the shared `brush`
# selection, so brushing one plot filters the others (a "crossfilter").
spec = {
    "params": {"brush": {"select": "crossfilter"}},
    "vconcat": [
        {
            "plot": [
                {
                    "mark": "dot",
                    "data": {"from": "penguins", "filterBy": "$brush"},
                    "x": "flipper_length",
                    "y": "body_mass",
                    "fill": "species",
                    "r": 2.5,
                },
                {"select": "intervalXY", "as": "$brush"},
            ],
            "xDomain": "Fixed",
            "yDomain": "Fixed",
            "width": 600,
            "height": 300,
        },
        {
            "plot": [
                {
                    "mark": "rectY",
                    "data": {"from": "penguins", "filterBy": "$brush"},
                    "x": {"bin": "flipper_length"},
                    "y": {"count": ""},
                    "fill": "steelblue",
                    "inset": 0.5,
                },
                {"select": "intervalX", "as": "$brush"},
            ],
            "xDomain": "Fixed",
            "width": 600,
            "height": 150,
        },
    ],
}

app_ui = ui.page_fillable(
    ui.output_text("params"),
    ui.output_text("n_selected"),
    ui.card(output_widget("dashboard"), style="height: 550px"),
)


def server(input, output, session):
    @render_mosaic_widget
    def dashboard():
        return MosaicWidget(spec, data={"penguins": penguins})

    @reactive.calc
    def selected():
        # Take the (debounced) dependency, then query with the current
        # predicates
        dashboard.params()
        return dashboard.data()

    @render.text
    def params():
        return str(dashboard.params())

    @render.text
    def n_selected():
        (count,) = selected().aggregate("count(*)").fetchall()[0]
        return str(count)


app = App(app_ui, server)
