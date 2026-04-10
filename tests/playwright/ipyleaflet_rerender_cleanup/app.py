from __future__ import annotations

import ipyleaflet as L
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
        m = L.Map(center=(52 + n, 360 - n), zoom=4)
        m.add(L.Marker(location=(52 + n, 360 - n)))
        return m


app = App(app_ui, server)
