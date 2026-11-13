from __future__ import annotations

from drawdata import ScatterWidget
from shiny.express import render, ui
from shinywidgets import render_drawdata

ui.page_opts(fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Draw a dataset (pick a class, then drag)")

    @render_drawdata
    def canvas():
        return ScatterWidget(width=800, height=400, n_classes=2)


@render.code
def summary():
    # .read("data") re-runs this whenever a new drawing batch syncs; a
    # plain `canvas.widget.data` read would only ever see the first value.
    df = canvas.read("data")
    return f"{len(df)} points drawn"
