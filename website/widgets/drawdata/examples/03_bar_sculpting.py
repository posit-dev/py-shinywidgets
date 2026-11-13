from __future__ import annotations

import pandas as pd
from drawdata import BarWidget
from shiny.express import render, ui
from shinywidgets import render_drawdata

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=(7, 5)):
    with ui.card(full_screen=True):
        ui.card_header("Sculpt a distribution by dragging the bars")

        @render_drawdata
        def hist():
            # A single collection name hides the collection-switcher and
            # Clear buttons that show up with the default two names.
            return BarWidget(collection_names=["height_cm"], y_max=2.0, n_bins=20)

    with ui.card(full_screen=True):
        ui.card_header("Summary, live")

        @render.code
        def summary():
            df = pd.DataFrame(hist.read("data"))
            # `data` is [] until the browser's first sync, so df may not
            # have a "value" column yet -- treat that as nothing raised
            drawn = df[df["value"] != 0] if "value" in df else df
            if drawn.empty:
                return "No bars raised yet."
            return (
                f"{len(drawn)} of {len(df)} bins raised\n"
                f"mean height: {drawn['value'].mean():.2f}\n"
                f"max height:  {drawn['value'].max():.2f}"
            )
