from __future__ import annotations

import plotly.graph_objects as go
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("plot"),
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

    @render_widget
    def plot():
        n = counter.get()
        return go.FigureWidget(
            data=[go.Scatter(x=[1, 2, 3], y=[n, n + 1, n + 2])],
            layout={"title": f"render {n}"},
        )


app = App(app_ui, server)
