from __future__ import annotations

import plotly.express as px
from pyobsplot import Plot
from shiny.express import ui

from shinywidgets import render_obsplot

ui.page_opts(title="Facets: small multiples for free", fillable=True)

gapminder = px.data.gapminder()
gapminder_2007 = gapminder[gapminder["year"] == 2007].reset_index(drop=True)

with ui.card(full_screen=True):
    ui.card_header("GDP per capita vs. life expectancy, by continent (2007)")

    @render_obsplot
    def faceted():
        return Plot.plot(
            {
                "height": 300,
                "x": {"type": "log", "label": "GDP per capita"},
                "fx": {"label": None},
                "marks": [
                    # Adding an "fx"/"fy" channel to a mark is enough: Plot
                    # facets automatically, no separate facet() call needed.
                    Plot.dot(
                        gapminder_2007,
                        {
                            "x": "gdpPercap",
                            "y": "lifeExp",
                            "fx": "continent",
                            "r": "pop",
                            "fill": "continent",
                        },
                    ),
                ],
            }
        )
