# Title: Table row to highlight
# Summary: Select rows in a table and the matching points light up in a
#     scatter plot, updated in place so pan/zoom state is preserved. The
#     cross-widget "table row -> highlight" pattern -- swap in your own
#     data frame and the x/y columns to plot.
# Bucket: template
# Widgets: itables, plotly
# Pattern: table row selection -> in-place highlight
# Run: uv run shiny run app.py
# Data: plotly.express.data.gapminder() (142 countries, 2007), ships with plotly
#
# Source: docs/widget-guides/articles/linked-views/examples/09_itables_selection_to_plotly_inplace.py

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
from itables.widget import ITable
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_itables, render_plotly

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="Selection highlights a plot", fillable=True)

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card(full_screen=True):
        ui.card_header("Select rows here")

        @render_itables
        def table():
            return ITable(countries, select=True)

    with ui.card(full_screen=True):
        ui.card_header("...to highlight them here")

        @render_plotly
        def scatter():
            fig = go.FigureWidget(
                go.Scatter(
                    x=countries["gdpPercap"],
                    y=countries["lifeExp"],
                    mode="markers",
                    marker={"color": "#bbb", "size": 8},
                    text=countries["country"],
                )
            )
            fig.update_xaxes(type="log", title="GDP per capita")
            fig.update_yaxes(title="Life expectancy")
            return fig


@reactive.effect
def _highlight_selection():
    selected = set(table.selected_rows())
    with reactive.isolate():
        # In place: the scatter keeps its zoom/pan state across selections,
        # instead of rebuilding (and resending) the whole figure.
        scatter.widget.data[0].marker.color = [
            "#e41a1c" if i in selected else "#bbb" for i in range(len(countries))
        ]
