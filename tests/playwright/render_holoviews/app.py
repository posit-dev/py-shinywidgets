from __future__ import annotations

import holoviews as hvl
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_holoviews

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("hv"),
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

    @render_holoviews
    def hv():
        n = counter.get()
        return hvl.Curve([n, n + 1, n + 2])


app = App(app_ui, server)
