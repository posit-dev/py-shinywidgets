from __future__ import annotations

import base64

import ipywidgets as widgets
from shiny import App, ui
from shinywidgets import output_widget, render_widget

# A 1x1 transparent PNG
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

app_ui = ui.page_fillable(
    ui.input_select("color", "Color", ["red", "green", "blue"]),
    output_widget("out"),
    output_widget("text_out"),
    output_widget("button_out"),
    output_widget("image_out"),
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

    @render_widget
    def button_out():
        # The view's root IS a <button> holding its description as text
        # (no element children), like text_out but at the root
        input.color()
        return widgets.Button(description="apply")

    @render_widget
    def image_out():
        # The view's root is an <img>: renderable with neither children nor text
        input.color()
        return widgets.Image(value=PNG, format="png")


app = App(app_ui, server)
