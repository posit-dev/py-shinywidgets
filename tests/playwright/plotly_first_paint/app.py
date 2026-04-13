from __future__ import annotations

import plotly.graph_objects as go
from shiny import App, ui
from shinywidgets import output_widget, render_plotly

app_ui = ui.page_fillable(
    ui.input_checkbox("show_points", "Show points", value=True),
    output_widget("plot"),
)


def server(input, output, session):
    @render_plotly
    def plot():
        return go.FigureWidget(
            data=[
                go.Scattergl(
                    x=list(range(1000)),
                    y=list(range(1000)),
                    mode="markers",
                )
            ],
            layout={"showlegend": False},
        )


app = App(app_ui, server)
