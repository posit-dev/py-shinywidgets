from __future__ import annotations

from drawdata import ScatterWidget
from shiny.express import render, ui
from shinywidgets import render_drawdata

ui.page_opts(fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Draw a couple of strokes")

    @render_drawdata
    def canvas():
        return ScatterWidget(width=800, height=400, n_classes=2)


@render.code
def state():
    # Each call to .read("data") re-runs this on every *synced* change to
    # "data" -- see "Gotchas" for why the very first stroke of a session
    # doesn't show up here until a second one starts.
    data = canvas.read("data")
    batches = sorted({d["batch"] for d in data})
    return f"{len(data)} points synced to Python, across batches {batches}"
