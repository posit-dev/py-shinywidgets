from __future__ import annotations

import ipyleaflet as L
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget


N_MARKERS = 960

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    output_widget("plot"),
)


def marker_locations(offset: int) -> list[tuple[float, float]]:
    base_lat = 37.75 + (offset * 0.01)
    base_lng = -122.45 + (offset * 0.01)
    locations: list[tuple[float, float]] = []
    for i in range(N_MARKERS):
        row = i // 32
        col = i % 32
        locations.append((base_lat + (row * 0.005), base_lng + (col * 0.005)))
    return locations


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render_widget
    def plot():
        n = counter.get()
        markers = [
            L.CircleMarker(
                location=location,
                radius=4,
                color="royalblue",
                fill_color="royalblue",
                fill_opacity=0.7,
            )
            for location in marker_locations(n)
        ]
        m = L.Map(center=(37.9 + (n * 0.01), -122.2 + (n * 0.01)), zoom=9)
        m.add(L.LayerGroup(layers=markers))
        return m


app = App(app_ui, server)
