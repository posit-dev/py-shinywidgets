# Live feed with presets (template)
#
# A streaming Perspective grid with two one-click presets (pivot / reset) and
# a live readout of the viewer's current filter -- a starting point for any
# "rows arriving over time, user pivots/filters them" app.
#
# Bucket: template (~70 lines)
# Run: uv run shiny run docs/widget-guides/perspective/gallery/template_live_feed.py
# Data: synthesized in-process (random notional for real stock tickers)
#
# NOTE: this is a `#`-comment header, not a module docstring. A bare
# triple-quoted string at module scope is a no-op in a normal script, but
# Shiny Express treats every top-level expression statement as something to
# render, so a docstring here would print itself as page text.

from __future__ import annotations

import random

import pandas as pd
from perspective import Server
from perspective.widget import PerspectiveWidget
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_perspective

ui.page_opts(title="Live feed", fillable=True)

SYMBOLS = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA"]

PRESETS = {
    "pivot": {
        "group_by": ["symbol"],
        "sort": [["notional", "desc"]],
        "aggregates": {"notional": "sum"},
    },
    "reset": {"group_by": [], "sort": [], "filter": []},
}


def make_rows(n: int, start: int) -> list[dict]:
    return [
        {
            "id": start + i,
            "symbol": random.choice(SYMBOLS),
            "notional": round(random.uniform(1_000, 50_000), 2),
        }
        for i in range(n)
    ]


with ui.layout_columns(col_widths=[3, 9]):
    with ui.card():
        ui.card_header("Controls")
        ui.input_action_button("preset_pivot", "Pivot by symbol")
        ui.input_action_button("preset_reset", "Reset")

        @render.code
        def filter_state():
            return f"filter: {grid.filter()}"

    with ui.card(full_screen=True):

        @render_perspective
        def grid():
            # `limit` keeps this a rolling window no matter how long it runs.
            table = (
                Server()
                .new_local_client()
                .table(pd.DataFrame(make_rows(30, 0)), limit=1000)
            )
            return PerspectiveWidget(
                table,
                plugin="Y Bar",
                columns=["notional"],
                group_by=["symbol"],
                aggregates={"notional": "avg"},
            )


next_id = reactive.value(30)


@reactive.effect
def _stream():
    reactive.invalidate_later(0.5)
    with reactive.isolate():
        start = next_id.get()
    next_id.set(start + 5)
    grid.widget.update(make_rows(5, start))


@reactive.effect
@reactive.event(input.preset_pivot)
def _():
    grid.widget.restore(**PRESETS["pivot"])


@reactive.effect
@reactive.event(input.preset_reset)
def _():
    grid.widget.restore(**PRESETS["reset"])
