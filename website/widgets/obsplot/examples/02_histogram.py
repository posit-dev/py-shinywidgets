from __future__ import annotations

import plotly.express as px
from pyobsplot import Plot
from shiny.express import ui

from shinywidgets import render_obsplot

ui.page_opts(title="binX + rectY: a histogram from raw rows", fillable=True)

gapminder = px.data.gapminder()
# Filtering a pandas DataFrame leaves a non-contiguous index; pyobsplot 0.5.4
# chokes on that (see the Gotchas section), so reset it before plotting.
gapminder_2007 = gapminder[gapminder["year"] == 2007].reset_index(drop=True)

with ui.card(full_screen=True):
    ui.card_header("Life expectancy by continent, 2007")

    @render_obsplot
    def hist():
        return Plot.plot(
            {
                "color": {"legend": True},
                "marks": [
                    Plot.rectY(
                        gapminder_2007,
                        Plot.binX(
                            {"y": "count"},
                            {"x": "lifeExp", "fill": "continent"},
                        ),
                    ),
                    Plot.ruleY([0]),
                ],
            }
        )
