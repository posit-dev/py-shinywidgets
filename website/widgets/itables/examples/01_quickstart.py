from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny.express import ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="itables quickstart", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("142 countries, 2007 (click a row to select it)")

    @render_itables
    def table():
        return ITable(countries, select=True)
