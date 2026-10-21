from __future__ import annotations

import ipywidgets as widgets
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from shiny import App, reactive, render, ui
from shinywidgets import as_widget, output_widget, render_matplotlib, render_widget

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("mpl"),
    ui.input_action_button("swap", "Swap container child"),
    output_widget("container"),
)


def small_canvas(n: int) -> widgets.Widget:
    fig = Figure(figsize=(3, 2))
    fig.subplots().plot([1, 2, 3], [n, n + 1, n])
    return as_widget(fig)


def server(input, output, session):
    counter = reactive.value(0)
    box = widgets.VBox([small_canvas(0)])

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_matplotlib
    def mpl():
        n = counter.get()
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [n, n + 1, n + 2])
        return fig

    # ipywidgets itself (not shinywidgets' teardown) removes the old canvas view
    @render_widget
    def container():
        return box

    @reactive.effect
    @reactive.event(input.swap)
    def _():
        box.children = [small_canvas(input.swap())]


app = App(app_ui, server)
