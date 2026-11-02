from __future__ import annotations

import ipyleaflet as L
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipyleaflet

# Both accessors' first reads are gated behind action buttons, so nothing
# reads them at startup. A gesture made before the button click then
# exercises the accessor's attach timing (see the tests).

app_ui = ui.page_fluid(
    ui.input_action_button("read_zoom", "Read zoom"),
    ui.input_action_button("read_clicked", "Read clicked"),
    ui.output_text("zoom"),
    ui.output_text("clicked"),
    ui.output_text("synced_zoom"),
    ui.card(output_widget("map"), height="450px"),
)


def server(input, output, session):
    @render_ipyleaflet
    def map():
        return L.Map(center=(52, 0), zoom=4)

    @render.text
    @reactive.event(input.read_zoom)
    def zoom():
        return str(map.zoom())

    # Sentinel: the map's raw zoom trait (no accessor involved), so a test
    # can wait until a gesture has synced from browser to server before
    # triggering a gated read.
    @render.text
    def synced_zoom():
        return str(reactive_read(map.widget, "zoom"))

    @render.text
    @reactive.event(input.read_clicked)
    def clicked():
        c = map.clicked()
        return "" if c is None else str(c["coordinates"])


app = App(app_ui, server)
