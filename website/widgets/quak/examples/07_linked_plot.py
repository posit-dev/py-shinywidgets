from __future__ import annotations

import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_plotly, render_quak

ui.page_opts(title="quak filter -> plotly chart", fillable=True)

gapminder = px.data.gapminder()

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Brush a histogram or click a continent bar")

        @render_quak
        def table():
            return gapminder

    with ui.card(full_screen=True):
        ui.card_header("Life expectancy by continent, filtered rows only")

        @render_plotly
        def chart():
            # Re-runs (debounced) whenever table.sql() changes, so the bars
            # always describe exactly the rows quak is showing.
            filtered = table.data().df()
            return px.box(filtered, x="continent", y="lifeExp", color="continent")
