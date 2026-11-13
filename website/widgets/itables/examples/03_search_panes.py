from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny.express import ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="SearchPanes", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Check continents in the pane to filter the table")

    @render_itables
    def table():
        # SearchPanes draws a faceted filter panel (one pane per listed column,
        # with row counts) above the table; checking a value filters like a
        # column search would.
        return ITable(
            countries,
            layout={"top1": "searchPanes"},
            searchPanes={"layout": "columns-1", "columns": [1]},
            select=True,
        )
