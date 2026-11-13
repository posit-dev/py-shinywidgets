from __future__ import annotations

import plotly.express as px
from pyobsplot import Plot
from shiny import reactive
from shiny.express import input, ui

from shinywidgets import render_obsplot

ui.page_opts(title="Scrubbing a year without re-rendering", fillable=True)

gapminder = px.data.gapminder()
years = sorted(gapminder["year"].unique().tolist())

ui.input_slider(
    "year", "Year", min=years[0], max=years[-1], value=years[0], step=5, sep=""
)


def spec_for_year(year: int) -> dict:
    year_rows = gapminder[gapminder["year"] == year].reset_index(drop=True)
    return {
        "x": {"type": "log", "label": "GDP per capita"},
        "y": {"domain": [20, 85], "label": "Life expectancy"},
        "r": {"range": [2, 24]},
        "color": {"legend": True},
        "marks": [
            Plot.dot(
                year_rows,
                {"x": "gdpPercap", "y": "lifeExp", "r": "pop", "fill": "continent"},
            ),
        ],
    }


with ui.card(full_screen=True):

    @render_obsplot
    def bubble():
        return Plot.plot(spec_for_year(years[0]))


@reactive.effect
def _():
    # Every slider tick replaces the spec in place; the output never shows
    # Shiny's "recalculating" overlay and the JS bundle is sent only once.
    bubble.widget.spec = spec_for_year(input.year())
