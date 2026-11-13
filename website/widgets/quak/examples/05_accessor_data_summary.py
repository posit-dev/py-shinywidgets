from __future__ import annotations

import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_quak

ui.page_opts(title="quak data() accessor", fillable=True)

gapminder = px.data.gapminder()

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_quak
        def table():
            return gapminder

    with ui.layout_columns(col_widths=12):
        with ui.value_box():
            "Countries x years selected"

            @render.text
            def n_rows():
                return f"{table.data().aggregate('count(*)').fetchall()[0][0]:,}"

        with ui.value_box():
            "Median life expectancy"

            @render.text
            def median_life_exp():
                value = table.data().aggregate("median(lifeExp)").fetchall()[0][0]
                return f"{value:.1f} years"
