from __future__ import annotations

import ipywidgets as widgets
import mapwidget.leaflet
import mapwidget.maplibre
import mapwidget.openlayers
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_mapwidget

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("map_zoom"),
    ui.output_text("leaflet_clicked"),
    ui.card(
        output_widget("map"),
        id="fill_card",
        height="700px",
    ),
    ui.card(
        output_widget("leaflet_map"),
        id="small_card",
        height="250px",
    ),
    ui.card(
        output_widget("ol_map"),
        id="ol_card",
        height="350px",
    ),
    output_widget("map_output_height", height="300px"),
    output_widget("mapml_output_height", height="300px"),
    output_widget("map_explicit_height"),
    output_widget("map_layout_height"),
    output_widget("map_auto_height", height="auto"),
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

    @render_mapwidget
    def map():
        n = counter.get()
        return mapwidget.maplibre.Map(center=[40 + n, -100], zoom=4)

    @render_mapwidget
    def leaflet_map():
        return mapwidget.leaflet.Map(center=[52, 5], zoom=6)

    @render_mapwidget
    def ol_map():
        return mapwidget.openlayers.Map(center=[52, 5], zoom=6)

    # A default-height map in an explicit-height output sizes to the output
    @render_mapwidget
    def map_output_height():
        return mapwidget.leaflet.Map()

    # The maplibre backend puts the inline height on its root element (the
    # leaflet backend puts it on an inner container), so exercise both in an
    # explicit-height output
    @render_mapwidget
    def mapml_output_height():
        return mapwidget.maplibre.Map()

    # An explicit map height is respected (no filling)
    @render_mapwidget
    def map_explicit_height():
        return mapwidget.maplibre.Map(height="800px")

    # An explicit Layout height must size the map itself, not just the widget
    # container (the backend's default 600px inner map would overflow it)
    @render_mapwidget
    def map_layout_height():
        return mapwidget.leaflet.Map(layout=widgets.Layout(height="300px"))

    # `height: auto` is not a definite height, so the map keeps its own
    # default height rather than collapsing to 0
    @render_mapwidget
    def map_auto_height():
        return mapwidget.maplibre.Map()

    @render.text
    def map_zoom():
        return str(reactive_read(map.widget, "zoom"))

    @render.text
    def leaflet_clicked():
        return str(reactive_read(leaflet_map.widget, "clicked_latlng"))


app = App(app_ui, server)
