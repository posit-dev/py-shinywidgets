from __future__ import annotations

import plotly.express as px
from pyobsplot import Plot
from shiny.express import ui

from shinywidgets import render_obsplot

ui.page_opts(title="groupY: aggregate without leaving Python", fillable=True)

gapminder = px.data.gapminder()
gapminder_2007 = gapminder[gapminder["year"] == 2007].reset_index(drop=True)

with ui.card(full_screen=True):
    ui.card_header("Average life expectancy by continent, 2007")

    @render_obsplot
    def bars():
        return Plot.plot(
            {
                # Plot under-sizes the left margin for a categorical axis
                # with an axis title, clipping the tick labels; widen it and
                # drop the title ("continent" is obvious from the labels).
                "marginLeft": 80,
                "y": {"label": None},
                "marks": [
                    # groupY computes the mean per continent in the browser;
                    # the rows go over the wire as-is.
                    Plot.barX(
                        gapminder_2007,
                        Plot.groupY(
                            {"x": "mean"},
                            {"y": "continent", "x": "lifeExp", "sort": {"y": "-x"}},
                        ),
                    ),
                    Plot.ruleX([0]),
                ],
            }
        )
