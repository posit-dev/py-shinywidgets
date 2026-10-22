from __future__ import annotations

from maplibre import Map
from maplibre.ipywidget import MapWidget
from shiny import App, ui
from shinywidgets import output_widget, render_maplibre

app_ui = ui.page_fluid(
    ui.layout_columns(
        ui.card(output_widget("fill"), full_screen=True),
        ui.card(output_widget("widget_height")),
        ui.navset_card_tab(
            ui.nav_panel("Text", "Click the other tab to show the map"),
            ui.nav_panel("Map", output_widget("hidden_tab")),
            id="tabs",
        ),
        height="520px",
    ),
    ui.layout_columns(
        output_widget("output_250", height="250px"),
        output_widget("output_600", height="600px"),
        # Outputs with no definite height to fill (and no explicit height)
        ui.div(output_widget("unfillable_default")),
        ui.div(output_widget("unfillable_600")),
    ),
)


def server(input, output, session):
    @render_maplibre
    def fill():
        return Map()

    @render_maplibre
    def widget_height():
        return MapWidget(height=200)

    @render_maplibre
    def hidden_tab():
        return Map()

    @render_maplibre
    def output_250():
        return Map()

    @render_maplibre
    def output_600():
        return Map()

    @render_maplibre
    def unfillable_default():
        return Map()

    @render_maplibre
    def unfillable_600():
        return MapWidget(height=600)


app = App(app_ui, server)
