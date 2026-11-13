from __future__ import annotations

import plotly.express as px
from pyobsplot import Plot
from shiny.express import ui

from shinywidgets import render_obsplot

ui.page_opts(title="dodge: a beeswarm with no overlap", fillable=True)

gapminder = px.data.gapminder()
gapminder_2007 = gapminder[gapminder["year"] == 2007].reset_index(drop=True)

with ui.card(full_screen=True):
    ui.card_header("Life expectancy, one dot per country (2007)")

    @render_obsplot
    def beeswarm():
        return Plot.plot(
            {
                "height": 320,
                "color": {"legend": True},
                "marks": [
                    # dodge nudges overlapping dots apart along y, so every
                    # country gets its own visible dot instead of a blob.
                    Plot.dotX(
                        gapminder_2007,
                        Plot.dodgeY(
                            {"x": "lifeExp", "fill": "continent", "r": 3}
                        ),
                    ),
                ],
            }
        )
