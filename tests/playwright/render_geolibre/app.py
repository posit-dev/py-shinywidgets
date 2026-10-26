from __future__ import annotations

import json

from geolibre import Map
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_geolibre

app_ui = ui.page_fillable(
    ui.layout_columns(
        ui.card(output_widget("map")),
        ui.card(output_widget("map_fixed")),
        ui.card(output_widget("map_output_height", height="400px")),
    ),
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("clicked"),
    ui.output_text("view"),
)


def server(input, output, session):
    counter = reactive.value(0)
    click = reactive.value(None)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_geolibre
    def map():
        input.rerender()
        m = Map(center=(-98.5, 39.8), zoom=4)
        m.on_click(lambda e: click.set(e))
        return m

    @render_geolibre
    def map_fixed():
        return Map(center=(-98.5, 39.8), zoom=4, height="500px")

    @render_geolibre
    def map_output_height():
        return Map(center=(-98.5, 39.8), zoom=4)

    @render.text
    def clicked():
        e = click.get()
        return "" if e is None else json.dumps(e["lngLat"])

    @render.text
    def view():
        project = reactive_read(map.widget, "project")
        mv = project.get("mapView", {})
        return json.dumps({"center": mv.get("center"), "zoom": mv.get("zoom")})


app = App(app_ui, server)
