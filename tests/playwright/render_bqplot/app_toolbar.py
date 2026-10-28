from __future__ import annotations

import bqplot
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_bqplot

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("interaction"),
    output_widget("fig", height="400px"),
)


def server(input, output, session):
    @render_bqplot
    def fig():
        input.rerender()
        x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
        return bqplot.Figure(
            marks=[
                bqplot.Lines(x=[1, 2, 3], y=[1, 2, 3], scales={"x": x_sc, "y": y_sc})
            ],
            axes=[
                bqplot.Axis(scale=x_sc),
                bqplot.Axis(scale=y_sc, orientation="vertical"),
            ],
            display_toolbar=True,
        )

    @render.text
    def interaction():
        return type(reactive_read(fig.widget, "interaction")).__name__


app = App(app_ui, server)
