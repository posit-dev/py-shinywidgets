from __future__ import annotations

import ipywidgets as widgets
from shiny import App, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fillable(
    ui.input_select("color", "Color", ["red", "green", "blue"]),
    output_widget("out"),
    output_widget("text_out"),
)


def server(input, output, session):
    @render_widget
    def out():
        color = input.color()
        return widgets.HTML(
            value=f"<div id='payload' style='background:{color};"
            f"padding:40px;color:white'>{color}</div>"
        )

    @render_widget
    def text_out():
        # Re-renders alongside `out` so tests can measure how long the
        # output stays hidden across a re-render
        input.color()
        return widgets.HTML(value="plain text")


app = App(app_ui, server)
