from __future__ import annotations

import ipyleaflet as L
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget


POINTS = [(63.1016, -151.5129)] * 1000


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
        m = L.Map(center=(POINTS[0][0], POINTS[0][1] + n * 0.01), zoom=2)
        markers = [
            L.CircleMarker(location=location, radius=3, stroke=False, fill_opacity=0.7)
            for location in POINTS
        ]
        m.add(L.LayerGroup(layers=markers))
        return m


app = App(app_ui, server)
