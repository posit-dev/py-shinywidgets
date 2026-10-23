from __future__ import annotations

import bqplot
from shiny import App, ui
from shinywidgets import output_widget, render_bqplot

app_ui = ui.page_fluid(output_widget("fig", height="300px"))


def server(input, output, session):
    @render_bqplot
    def fig():
        x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
        scatter = bqplot.Scatter(
            x=[1, 2, 3],
            y=[1, 3, 2],
            scales={"x": x_sc, "y": y_sc},
            tooltip=bqplot.Tooltip(fields=["x", "y"]),
        )
        return bqplot.Figure(marks=[scatter])


app = App(app_ui, server)
