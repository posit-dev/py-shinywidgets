from __future__ import annotations

import ipywidgets
from shiny import App, render, ui
from shinywidgets import output_widget, render_widget
from shinywidgets._lifecycle import get_lifecycle

app_ui = ui.page_fluid(
    ui.output_text("session_info"),
    output_widget("widget"),
)


def server(input, output, session):
    @render_widget
    def widget():
        return ipywidgets.HTML(value="epoch widget")

    @render.text
    def session_info():
        lifecycle = get_lifecycle(session.root_scope())
        snap = lifecycle.snapshot()
        return (
            f"ns={lifecycle.epoch.model_namespace} "
            f"records={snap.records} leases={snap.display_leases}"
        )


app = App(app_ui, server)
