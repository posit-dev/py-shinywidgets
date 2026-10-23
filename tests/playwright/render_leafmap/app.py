from __future__ import annotations

import ipyleaflet as L
from ipywidgets import Layout
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_leafmap

app_ui = ui.page_fluid(
    ui.output_text("bounds_text"),
    ui.card(
        output_widget("default_map"),
        id="fill_card",
        height="450px",
    ),
    output_widget("explicit_height_map", height="400px"),
    ui.card(
        output_widget("card_map"),
        id="small_card",
        height="250px",
    ),
)


def leafmap_map(**kwargs) -> L.Map:
    # leafmap's Map is an ipyleaflet.Map subclass defined in leafmap that sets
    # Layout.height to 600px by default. Mimic it without depending on leafmap:
    # the subclass's module is what makes shinywidgets treat it as leafmap's.
    Map = type("Map", (L.Map,), {"__module__": "leafmap.leafmap"})
    m = Map(center=(52, 0), zoom=4, **kwargs)
    if "layout" not in kwargs:
        m.layout.height = "600px"
    return m


def server(input, output, session):
    @render_leafmap
    def default_map():
        # No explicit height: leafmap's 600px default should be treated as unset
        m = leafmap_map()
        m.add(L.Marker(location=(52, 0)))
        return m

    @render_leafmap
    def explicit_height_map():
        # A height the user asked for is respected
        return leafmap_map(layout=Layout(height="250px"))

    @render_leafmap
    def card_map():
        return leafmap_map()

    @render.text
    def bounds_text():
        b = reactive_read(default_map.widget, "bounds")
        if not b:
            return ""
        return f"{b[0][0]:.0f},{b[0][1]:.0f}"


app = App(app_ui, server)
