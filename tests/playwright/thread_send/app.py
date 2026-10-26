from __future__ import annotations

import threading
import time

import ipywidgets
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.input_action_button("go", "Update from a thread"),
    output_widget("slider", height="60px"),
)


def server(input, output, session):
    @render_widget
    def slider():
        return ipywidgets.IntSlider(value=1, description="value")

    @reactive.effect
    @reactive.event(input.go)
    def _():
        w = slider.widget

        def worker() -> None:
            time.sleep(0.2)  # make sure the reactive cycle that handled the click is over
            w.value = 42  # ShinyComm.send() from a non-event-loop thread

        threading.Thread(target=worker, daemon=True).start()


app = App(app_ui, server)
