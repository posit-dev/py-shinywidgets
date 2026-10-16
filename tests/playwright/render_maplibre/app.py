from __future__ import annotations

from maplibre import Map
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_maplibre

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("map"),
    ui.output_text("map_clicked"),
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

    @render_maplibre
    def map():
        return Map()

    @render.text
    def map_clicked():
        return str(reactive_read(map.widget, "clicked"))


app = App(app_ui, server)
