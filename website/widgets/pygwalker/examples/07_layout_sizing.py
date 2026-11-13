import plotly.express as px
from shiny.express import ui

import globals  # noqa: F401 -- locks down DuckDB once per process; see globals.py
from shinywidgets import render_pygwalker

ui.page_opts(fillable=True)
tips = px.data.tips()

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card(full_screen=True):
        ui.card_header("Fills the card (full_screen enabled)")

        @render_pygwalker
        def fill_explorer():
            return tips

    with ui.card():
        ui.card_header('Explicit height="420px" (scrolls inside)')

        @render_pygwalker(height="420px")
        def fixed_explorer():
            return tips
