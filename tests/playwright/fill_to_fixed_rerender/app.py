from __future__ import annotations

import ipywidgets
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.input_action_button("own_height", "Rerender with own height"),
    ui.output_text("render_count"),
    ui.div(
        output_widget("out"),
        id="fill_container",
        style="height: 400px;",
        class_="d-flex flex-column html-fill-container",
    ),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.own_height)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_widget
    def out():
        # Output isn't an @jupyter-widgets/controls widget, so it fills by default.
        # A height on its layout opts it out of filling.
        if counter.get() == 0:
            return ipywidgets.Output()
        return ipywidgets.Output(layout=ipywidgets.Layout(height="200px"))


app = App(app_ui, server)
