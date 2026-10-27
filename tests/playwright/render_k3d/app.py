from __future__ import annotations

import ipywidgets as widgets
import k3d
import numpy as np
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_k3d

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("camera"),
    ui.card(output_widget("fill_plot"), id="fill_card", height="420px"),
    output_widget("fixed_plot"),
    output_widget("sized_output", height="250px"),
    output_widget("intrinsic_output", height="auto"),
    output_widget("sized_layout"),
)


def make_plot(**kwargs) -> k3d.plot.Plot:
    rng = np.random.default_rng(0)
    positions = rng.random((200, 3), dtype=np.float32)
    plot = k3d.plot(**kwargs)
    plot += k3d.points(positions, point_size=0.05, color=0xFF0000)
    return plot


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_k3d
    def fill_plot():
        counter.get()
        return make_plot()

    @render_k3d
    def fixed_plot():
        return make_plot(height=300)

    @render_k3d
    def sized_output():
        return make_plot()

    @render_k3d
    def intrinsic_output():
        return make_plot()

    @render_k3d
    def sized_layout():
        plot = make_plot()
        plot.layout = widgets.Layout(height="300px")
        return plot

    @render.text
    def camera():
        return str(reactive_read(fill_plot.widget, "camera"))


app = App(app_ui, server)
