from __future__ import annotations

import ipywidgets
from shiny import App, module, reactive, render, ui
from shinywidgets import output_widget, render_widget
from shinywidgets._shinywidgets import WIDGET_INSTANCE_MAP


def live_sliders() -> int:
    return sum(
        isinstance(w, ipywidgets.IntSlider) for w in WIDGET_INSTANCE_MAP.values()
    )


@module.ui
def slider_ui():
    return [
        ui.input_action_button("rerender", "Rerender"),
        ui.output_text("count"),
        output_widget("w"),
    ]


@module.server
def slider_server(input, output, session):
    counter = reactive.value(0)
    # Lets the count output re-render only after the widget is (re)built,
    # so the widget count it reports is never stale.
    rendered = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render_widget
    def w():
        counter.get()
        widget = ipywidgets.IntSlider()
        with reactive.isolate():
            rendered.set(rendered.get() + 1)
        return widget

    @render.text
    def count():
        rendered.get()
        return f"renders={counter.get()} widgets={live_sliders()}"


app_ui = ui.page_fluid(slider_ui("mod"))


def server(input, output, session):
    slider_server("mod")


app = App(app_ui, server)
