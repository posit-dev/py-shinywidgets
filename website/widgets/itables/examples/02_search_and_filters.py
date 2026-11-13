from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny.express import ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="Search and column filters", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Global search box (top right) plus a per-column filter row")

    @render_itables
    def table():
        # The global search box is on by default; column_filters adds one text
        # input per column, wired to DataTables' own column search.
        return ITable(countries, column_filters="header", select=True)
