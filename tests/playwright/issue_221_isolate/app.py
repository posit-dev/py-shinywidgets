from __future__ import annotations

import ipywidgets as widgets
import plotly.graph_objects as go
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget


app_ui = ui.page_fluid(
    ui.h4("plot_in"),
    output_widget("plot_in"),
    ui.h4("plot_out"),
    output_widget("plot_out"),
    ui.h4("slider_in"),
    output_widget("slider_in"),
    ui.h4("slider_out"),
    output_widget("slider_out"),
)


def server(input, output, session):
    tick = reactive.value(0)

    @reactive.effect
    def _ticker():
        reactive.invalidate_later(1)
        with reactive.isolate():
            tick.set(tick.get() + 1)

    def make_plot(val: int) -> go.FigureWidget:
        return go.FigureWidget(data=[go.Scatter(x=[1, 2, 3], y=[1, val + 1, 3])])

    @render_widget
    def plot_in():
        with reactive.isolate():
            current = tick.get()
            return make_plot(current)

    @render_widget
    def plot_out():
        with reactive.isolate():
            current = tick.get()
        return make_plot(current)

    @render_widget
    def slider_in():
        with reactive.isolate():
            current = tick.get()
            return widgets.IntSlider(value=current, min=0, max=10)

    @render_widget
    def slider_out():
        with reactive.isolate():
            current = tick.get()
        return widgets.IntSlider(value=current, min=0, max=10)


app = App(app_ui, server)
