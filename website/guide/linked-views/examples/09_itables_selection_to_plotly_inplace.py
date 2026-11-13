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
