# Restyle the dashboard in place by assigning a new `.widget.spec`.
#
# Changing an existing MosaicWidget's `spec` trait re-renders it in the
# browser without creating a new widget, a new DuckDB connection, or sending
# another copy of Mosaic's JavaScript bundle. The tradeoff: Mosaic rebuilds
# the whole dashboard from the new spec, so the current selection resets.

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_mosaic_widget

PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["flipper_length_mm"])


def make_spec(fill: str) -> dict:
    return {
        "params": {"brush": {"select": "crossfilter"}},
        "plot": [
            {
                "mark": "rectY",
                "data": {"from": "penguins", "filterBy": "$brush"},
                "x": {"bin": "flipper_length_mm"},
                "y": {"count": ""},
                "fill": fill,
                "inset": 0.5,
            },
            {"select": "intervalX", "as": "$brush"},
        ],
        "xDomain": "Fixed",
        "width": 600,
        "height": 260,
    }


ui.page_opts(title="Restyle in place", fillable=True)

ui.input_radio_buttons(
    "color", "Bar color", choices=["steelblue", "darkorange", "seagreen"]
)

with ui.card(full_screen=True):

    @render_mosaic_widget
    def dashboard():
        # The render function must not depend on input.color(): that would
        # rebuild the whole widget on every color change, which is exactly
        # what the in-place update below avoids.
        with reactive.isolate():
            color = input.color()
        return MosaicWidget(make_spec(color), data={"penguins": penguins})

    @reactive.effect
    def _restyle():
        color = input.color()
        with reactive.isolate():
            w = dashboard.widget
            if w is not None:
                w.spec = make_spec(color)
