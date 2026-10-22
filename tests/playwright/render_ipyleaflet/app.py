from __future__ import annotations

import ipyleaflet as L
from ipywidgets import Layout
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipyleaflet

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("zoom_text"),
    ui.card(
        output_widget("lmap"),
        id="fill_card",
        height="450px",
    ),
    ui.card(
        output_widget("map_small_card"),
        id="small_card",
        height="250px",
    ),
    output_widget("map_output_height", height="300px"),
    output_widget("map_tall", height="600px"),
    output_widget("map_layout_height"),
    output_widget("map_auto_height", height="auto"),
    output_widget("map_layout_in_output_height", height="300px"),
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

    @render_ipyleaflet
    def lmap():
        n = counter.get()
        m = L.Map(center=(52 + n, 360 - n), zoom=4)
        m.add(L.Marker(location=(52 + n, 360 - n)))
        return m

    @render_ipyleaflet
    def map_output_height():
        return L.Map(center=(52, 360), zoom=4)

    @render_ipyleaflet
    def map_small_card():
        return L.Map(center=(52, 360), zoom=4)

    @render_ipyleaflet
    def map_tall():
        return L.Map(center=(52, 360), zoom=4)

    @render_ipyleaflet
    def map_layout_height():
        return L.Map(center=(52, 360), zoom=4, layout=Layout(height="250px"))

    @render_ipyleaflet
    def map_auto_height():
        return L.Map(center=(52, 360), zoom=4)

    @render_ipyleaflet
    def map_layout_in_output_height():
        return L.Map(center=(52, 360), zoom=4, layout=Layout(height="250px"))

    @render.text
    def zoom_text():
        return str(reactive_read(lmap.widget, "zoom"))


app = App(app_ui, server)
