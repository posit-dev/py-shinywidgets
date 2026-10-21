from __future__ import annotations

import matplotlib.pyplot as plt
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_matplotlib

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("mpl"),
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

    @render_matplotlib
    def mpl():
        n = counter.get()
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [n, n + 1, n + 2])
        return fig


app = App(app_ui, server)
