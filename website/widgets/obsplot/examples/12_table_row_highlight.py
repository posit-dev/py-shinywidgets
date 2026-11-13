from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from pyobsplot import Plot
from shiny import reactive
from shiny.express import ui

from shinywidgets import render_itables, render_obsplot

ui.page_opts(title="Table row selection highlights a point", fillable=True)

gapminder_2007 = px.data.gapminder().query("year == 2007").reset_index(drop=True)
cols = ["country", "continent", "lifeExp", "gdpPercap"]


def spec(country: str | None) -> dict:
    marks = [
        Plot.dot(
            gapminder_2007,
            {"x": "gdpPercap", "y": "lifeExp", "fill": "continent", "r": 3},
        ),
    ]
    if country is not None:
        row = gapminder_2007[gapminder_2007["country"] == country].reset_index(
            drop=True
        )
        marks.append(
            Plot.dot(
                row,
                {
                    "x": "gdpPercap",
                    "y": "lifeExp",
                    "r": 9,
                    "stroke": "black",
                    "strokeWidth": 2,
                },
            )
        )
    return {"x": {"type": "log", "label": "GDP per capita"}, "marks": marks}


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Select a row")

        @render_itables
        def table():
            return ITable(gapminder_2007[cols], select=True, lengthMenu=[5])

    with ui.card(full_screen=True):
        ui.card_header("Selected country")

        @render_obsplot
        def plot():
            return Plot.plot(spec(None))


@reactive.effect
def _():
    rows = table.selected_rows()
    country = gapminder_2007.iloc[rows[0]]["country"] if rows else None
    plot.widget.spec = spec(country)
