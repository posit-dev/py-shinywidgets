from __future__ import annotations

import plotly.express as px
from pyobsplot import Plot
from shiny import reactive
from shiny.express import ui

from shinywidgets import render_obsplot, render_plotly

ui.page_opts(title="Lasso-select in Plotly, filter an Observable Plot chart", fillable=True)

gapminder_2007 = px.data.gapminder().query("year == 2007").reset_index(drop=True)


def hist_spec(data) -> dict:
    return {
        "x": {"domain": [20, 85], "label": "Life expectancy"},
        "marks": [
            Plot.rectY(data, Plot.binX({"y": "count"}, {"x": "lifeExp"})),
            Plot.ruleY([0]),
        ],
    }


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Lasso-select countries")

        @render_plotly
        def scatter():
            fig = px.scatter(
                gapminder_2007,
                x="gdpPercap",
                y="lifeExp",
                color="continent",
                log_x=True,
                custom_data=[gapminder_2007.index],
            )
            return fig.update_layout(dragmode="select")

    with ui.card(full_screen=True):
        ui.card_header("Life expectancy of the selection")

        @render_obsplot
        def hist():
            return Plot.plot(hist_spec(gapminder_2007))


@reactive.effect
def _():
    rows = scatter.selected_rows(gapminder_2007)
    # selected_rows() keeps the original pandas index of the selected rows,
    # which pyobsplot 0.5.4 can't serialize unless it starts at 0 (see the
    # Gotchas section) -- reset it before handing the frame to Plot.
    data = rows.reset_index(drop=True) if len(rows) else gapminder_2007
    hist.widget.spec = hist_spec(data)
