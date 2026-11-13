from __future__ import annotations

import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_quak

ui.page_opts(title="quak sql() accessor", fillable=True)
ui.tags.style("pre { white-space: pre-wrap; overflow-wrap: anywhere; }")

gapminder = px.data.gapminder()

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_quak
        def table():
            return gapminder

    with ui.card():
        ui.card_header("table.sql()")

        @render.code
        def sql():
            # No req() needed: this cancels on its own while quak's query is
            # still the empty string it syncs during initialization.
            return table.sql()
