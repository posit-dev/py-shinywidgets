from __future__ import annotations

import bqplot
import bqplot.pyplot as bplt
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_bqplot

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("selected"),
    ui.card(
        ui.card_header("bqplot in a fixed-height card"),
        output_widget("fig"),
        height="400px",
    ),
    output_widget("fig_height", height="250px"),
    output_widget("fig_layout"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_bqplot
    def fig():
        counter.get()
        bplt.figure(title="pyplot interface")
        bplt.scatter(
            [1, 2, 3, 4], [1, 4, 2, 3], interactions={"click": "select"}, colors=["red"]
        )
        return bplt.current_figure()

    @render_bqplot
    def fig_height():
        x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
        return bqplot.Figure(
            title="height on output_widget()",
            marks=[
                bqplot.Lines(x=[1, 2, 3], y=[1, 2, 3], scales={"x": x_sc, "y": y_sc})
            ],
            axes=[
                bqplot.Axis(scale=x_sc),
                bqplot.Axis(scale=y_sc, orientation="vertical"),
            ],
        )

    @render_bqplot
    def fig_layout():
        x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
        return bqplot.Figure(
            title="height on the figure's layout",
            marks=[
                bqplot.Lines(x=[1, 2, 3], y=[1, 2, 3], scales={"x": x_sc, "y": y_sc})
            ],
            axes=[
                bqplot.Axis(scale=x_sc),
                bqplot.Axis(scale=y_sc, orientation="vertical"),
            ],
            layout={"height": "300px"},
        )

    @render.text
    def selected():
        scatter = fig.widget.marks[0]
        return str(reactive_read(scatter, "selected"))


app = App(app_ui, server)
