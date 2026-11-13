from __future__ import annotations

import random

import pandas as pd
from perspective import Server
from perspective.widget import PerspectiveWidget
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_perspective

ui.page_opts(title="Streaming", fillable=True)

SYMBOLS = ["AAPL", "MSFT", "GOOG"]


def make_rows(n: int, start: int) -> list[dict]:
    return [
        {
            "id": start + i,
            "symbol": random.choice(SYMBOLS),
            "notional": round(random.uniform(1_000, 50_000), 2),
        }
        for i in range(n)
    ]


@render_perspective
def grid():
    # `limit` keeps only the most recent 500 rows, so the table is a rolling
    # window no matter how long the stream runs.
    table = Server().new_local_client().table(pd.DataFrame(make_rows(20, 0)), limit=500)
    return PerspectiveWidget(
        table,
        plugin="Y Bar",
        columns=["notional"],  # otherwise the auto "index"/"id" columns plot too
        group_by=["symbol"],
        aggregates={"notional": "avg"},
    )


next_id = reactive.value(20)


@reactive.effect
def _stream():
    reactive.invalidate_later(0.5)
    with reactive.isolate():
        start = next_id.get()
    next_id.set(start + 5)
    # update() streams straight into every viewer attached to this table over
    # its comm -- no re-render, so any pivot/sort/filter the user set stays.
    grid.widget.update(make_rows(5, start))
