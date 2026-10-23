from __future__ import annotations

import plotly.graph_objects as go
from shiny import App, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fillable(
    ui.card(
        ui.card_header("Plotly reveal probe"),
        output_widget("scatterplot"),
        full_screen=True,
    )
)


def server(input, output, session):
    @render_widget
    def scatterplot():
        return go.FigureWidget(
            data=[
                go.Scattergl(
                    x=[1, 2, 3, 4, 5, 6],
                    y=[5.1, 4.9, 4.7, 4.6, 6.4, 6.9],
                    mode="markers",
                    marker={"size": 12},
                )
            ],
            layout={"showlegend": False},
        )


app = App(app_ui, server)
