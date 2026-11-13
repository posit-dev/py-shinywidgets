# `rate_delay=0`: see every raw params() update a brush drag sends.
#
# Left: default debounce (250ms) -- the counter settles once after each drag.
# Right: `rate_delay=0` -- the counter climbs during the drag itself, one tick
# per message the browser sends.

from __future__ import annotations

import pandas as pd
from mosaic_widget import MosaicWidget
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_mosaic_widget

PENGUINS_URL = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv"
penguins = pd.read_csv(PENGUINS_URL).dropna(subset=["flipper_length_mm"])

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
    "width": 400,
    "height": 220,
}

ui.page_opts(title="Rate limiting", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Default: debounce 250ms")

        @render_mosaic_widget
        def debounced():
            return MosaicWidget(spec, data={"penguins": penguins})

        update_count_debounced = reactive.value(0)

        @reactive.effect
        def _count_debounced():
            debounced.params()
            with reactive.isolate():
                update_count_debounced.set(update_count_debounced() + 1)

        @render.text
        def n_debounced():
            return f"params() fired {update_count_debounced()} times"

    with ui.card(full_screen=True):
        ui.card_header("rate_delay=0: every raw update")

        @render_mosaic_widget(rate_delay=0)
        def live():
            return MosaicWidget(spec, data={"penguins": penguins})

        update_count_live = reactive.value(0)

        @reactive.effect
        def _count_live():
            live.params()
            with reactive.isolate():
                update_count_live.set(update_count_live() + 1)

        @render.text
        def n_live():
            return f"params() fired {update_count_live()} times"
