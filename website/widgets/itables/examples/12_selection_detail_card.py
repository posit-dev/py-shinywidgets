from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny.express import render, ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="Click row for detail", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_itables
        def table():
            return ITable(countries, select=True)

    with ui.card():
        ui.card_header("Detail")

        @render.ui
        def detail():
            rows = table.selected_rows()
            if not rows:
                return ui.p("Click a row to see its detail.")
            row = countries.iloc[rows[-1]]
            return ui.TagList(
                ui.h5(row["country"]),
                ui.p(f"Continent: {row['continent']}"),
                ui.p(f"Life expectancy: {row['lifeExp']:.1f} years"),
                ui.p(f"Population: {row['pop']:,}"),
                ui.p(f"GDP per capita: ${row['gdpPercap']:,.0f}"),
            )
