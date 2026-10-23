from __future__ import annotations

import ipywidgets as w
from shiny import App, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(output_widget("plain"))


def server(input, output, session):
    @render_widget
    def plain():
        return w.HTML("no itables here")


app = App(app_ui, server)
