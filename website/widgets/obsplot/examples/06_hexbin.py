from __future__ import annotations

import plotly.express as px
from pyobsplot import Plot
from shiny.express import ui

from shinywidgets import render_obsplot

ui.page_opts(title="hexbin: 2D density for overplotted scatters", fillable=True)

gapminder = px.data.gapminder()

with ui.card(full_screen=True):
    ui.card_header("GDP per capita vs. life expectancy, every country-year")

    @render_obsplot
    def hexplot():
        return Plot.plot(
            {
                "x": {"type": "log", "label": "GDP per capita"},
                "color": {"scheme": "YlGnBu", "legend": True},
                "marks": [
                    Plot.dot(
                        gapminder,
                        Plot.hexbin(
                            {"fill": "count"},
                            {"x": "gdpPercap", "y": "lifeExp", "binWidth": 12},
                        ),
                    ),
                ],
            }
        )
