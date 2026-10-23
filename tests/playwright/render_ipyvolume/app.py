from __future__ import annotations

import ipyvolume as ipv
import ipywidgets as widgets
import numpy as np
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipyvolume

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("selection"),
    ui.output_text("camera"),
    ui.card(output_widget("fill_plot"), id="fill_card", height="420px"),
    output_widget("fixed_plot"),
    output_widget("sized_output", height="250px"),
    output_widget("sized_layout"),
)


def make_figure(**kwargs) -> ipv.widgets.Figure:
    rng = np.random.default_rng(0)
    x, y, z = rng.random((3, 500))
    ipv.figure(**kwargs)
    ipv.scatter(x, y, z, size=1, marker="sphere", color="red")
    return ipv.gcf()


def server(input, output, session):
    counter = reactive.value(0)
    selected = reactive.value("none")

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_ipyvolume
    def fill_plot():
        counter.get()
        fig = make_figure()
        fig.selector = "rectangle"
        fig.on_selection(lambda data: selected.set(str(data)))
        return fig

    @render_ipyvolume
    def fixed_plot():
        return make_figure(width=400, height=300)

    @render_ipyvolume
    def sized_output():
        return make_figure()

    @render_ipyvolume
    def sized_layout():
        fig = make_figure()
        fig.layout = widgets.Layout(height="300px")
        return fig

    @render.text
    def selection():
        return selected.get()

    @render.text
    def camera():
        return str(reactive_read(fill_plot.widget.camera, "position"))


app = App(app_ui, server)
