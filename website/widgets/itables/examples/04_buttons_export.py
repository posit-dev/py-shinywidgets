from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny.express import ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="Export buttons", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Copy and CSV export, no server-side code required")

    @render_itables
    def table():
        return ITable(countries, buttons=["copyHtml5", "csvHtml5"], select=True)
