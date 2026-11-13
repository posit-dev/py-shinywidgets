from __future__ import annotations

import altair as alt
import pandas as pd
from drawdata import BarWidget
from shiny.express import ui
from shinywidgets import render_altair, render_drawdata

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        ui.card_header("Sculpt two distributions (switch with the buttons)")

        @render_drawdata
        def hist():
            return BarWidget(n_bins=16)  # default collection_names: two groups

    with ui.card(full_screen=True):
        ui.card_header("Means, overlaid")

        @render_altair
        def overlay():
            df = pd.DataFrame(hist.read("data"))
            chart = (
                alt.Chart(df)
                .mark_bar(opacity=0.7)
                .encode(
                    x=alt.X("bin:O", title=None),
                    y=alt.Y("value:Q", title=None, stack=None),
                    color=alt.Color("collection:N", legend=alt.Legend(title=None)),
                )
            )
            return chart
