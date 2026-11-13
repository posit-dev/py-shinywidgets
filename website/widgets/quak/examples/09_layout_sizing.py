from __future__ import annotations

import plotly.express as px
from shiny.express import ui
from shinywidgets import render_quak

ui.page_opts(title="quak layout and sizing", fillable=True)

gapminder = px.data.gapminder()

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card(full_screen=True):
        ui.card_header("Fills its card (default)")

        @render_quak
        def fills():
            return gapminder

    with ui.card():
        ui.card_header('height="250px"')

        @render_quak(height="250px")
        def fixed():
            return gapminder
