from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny.express import render, ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="selected_rows()", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_itables
        def table():
            return ITable(countries, select=True)

    with ui.card():
        ui.card_header("table.selected_rows()")

        @render.code
        def rows():
            return str(table.selected_rows())

        @render.data_frame
        def selected():
            # Positions are into the data, not the display: they survive
            # sorting and searching.
            return countries.iloc[table.selected_rows()]
