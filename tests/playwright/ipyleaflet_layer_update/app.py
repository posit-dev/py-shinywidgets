"""Test app for issue #212: reactive effects that remove+add ipyleaflet layers."""

import ipyleaflet as L
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget

LOCATIONS = {
    "A": (40.7, -74.0),
    "B": (51.5, -0.1),
    "C": (48.9, 2.35),
}

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_selectize(
            "loc", "Location", choices=list(LOCATIONS.keys()), selected="A"
        ),
    ),
    output_widget("map"),
    fillable=True,
)


def server(input, output, session):
    @render_widget
    def map():
        m = L.Map(zoom=2, center=(0, 0), scroll_wheel_zoom=True)
        m.add(L.LayersControl(position="topleft"))
        return m

    @reactive.effect
    def _():
        loc = LOCATIONS[input.loc()]
        m = map.widget
        for layer in m.layers:
            if layer.name == "marker":
                m.remove(layer)
                break
        m.add(L.Marker(location=loc, draggable=False, name="marker"))

    @reactive.effect
    def _():
        loc = LOCATIONS[input.loc()]
        m = map.widget
        for layer in m.layers:
            if layer.name == "line":
                m.remove(layer)
                break
        m.add(L.Polyline(locations=[loc, (0, 0)], color="blue", weight=2, name="line"))


app = App(app_ui, server)
