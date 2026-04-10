from __future__ import annotations

import ipyleaflet as L
from shiny import App, ui
from shinywidgets import output_widget, render_widget


app_ui = ui.page_fluid(
    output_widget("map"),
)


def server(input, output, session):
    @render_widget
    def map():
        m = L.Map(center=(52.2, -1.5), zoom=5)

        def _on_interaction(**kwargs):
            if kwargs.get("type") != "click":
                return

            coords = kwargs.get("coordinates")
            if not coords:
                return

            map.widget.add_layer(L.Marker(location=coords))

        m.on_interaction(_on_interaction)
        return m


app = App(app_ui, server)
