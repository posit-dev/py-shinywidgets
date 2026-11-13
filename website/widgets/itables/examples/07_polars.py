from __future__ import annotations

import plotly.express as px
import polars as pl
from itables.widget import ITable
from shiny.express import render, ui
from shinywidgets import render_itables

countries = pl.from_pandas(
    px.data.gapminder()
    .query("year == 2007")[["country", "continent", "lifeExp", "pop", "gdpPercap"]]
    .reset_index(drop=True)
)

ui.page_opts(title="polars", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_itables
        def table():
            # itables accepts a polars DataFrame directly; no pandas conversion
            return ITable(countries, select=True)

    with ui.card():
        ui.card_header("Selected rows (polars indexing)")

        @render.data_frame
        def selected():
            return countries[table.selected_rows()]
