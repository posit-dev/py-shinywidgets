from __future__ import annotations

import ipywidgets as widgets
from shiny import App, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fillable(
    ui.input_select("color", "Color", ["red", "green", "blue"]),
    output_widget("out"),
)


def server(input, output, session):
    @render_widget
    def out():
        color = input.color()
        return widgets.HTML(
            value=f"<div id='payload' style='background:{color};"
            f"padding:40px;color:white'>{color}</div>"
        )


app = App(app_ui, server)
