# `dashboard.data()`: the selected rows as a lazy DuckDB relation.

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_mosaic_widget

PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["species", "flipper_length_mm", "body_mass_g"])

spec = {
    "params": {"brush": {"select": "crossfilter"}},
    "plot": [
        {
            "mark": "rectY",
            "data": {"from": "penguins", "filterBy": "$brush"},
            "x": {"bin": "flipper_length_mm"},
            "y": {"count": ""},
            "fill": "steelblue",
            "inset": 0.5,
        },
        {"select": "intervalX", "as": "$brush"},
    ],
    "xDomain": "Fixed",
    "width": 600,
    "height": 220,
}

ui.page_opts(title="data() accessor", fillable=True)

with ui.card(full_screen=True):

    @render_mosaic_widget
    def dashboard():
        return MosaicWidget(spec, data={"penguins": penguins})


# Take the (debounced) params() dependency once, then run one DuckDB query
# and share the result across outputs.
@reactive.calc
def selected():
    dashboard.params()
    return dashboard.data()


with ui.card():
    ui.card_header("Selected rows, aggregated in DuckDB")

    @render.code
    def summary():
        row = selected().aggregate(
            "count(*), round(avg(body_mass_g)) AS avg_mass"
        ).fetchall()[0]
        n, avg_mass = row
        return f"{n} penguins selected, average body mass {avg_mass} g"
