from __future__ import annotations

import plotly.express as px
from shiny import render
from shiny.express import ui
from shinywidgets import render_quak

ui.page_opts(title="quak filter -> CSV download", fillable=True)

gapminder = px.data.gapminder()

with ui.layout_columns(col_widths=[9, 3]):
    with ui.card(full_screen=True):

        @render_quak
        def table():
            return gapminder

    with ui.card():
        ui.card_header("Export")
        "Download exactly the rows currently shown (after sorting/filtering)."

        @render.download_button(filename="gapminder_filtered.csv", label="Download CSV")
        def download():
            # table.data() cancels (like an unrendered output) while quak's
            # query is still settling, so the button is simply unusable until
            # a query exists -- no error handling needed here.
            yield table.data().df().to_csv(index=False)
