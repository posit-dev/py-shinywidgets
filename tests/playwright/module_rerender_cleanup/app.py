from __future__ import annotations

import ipywidgets
from shiny import App, Session, module, reactive, render, ui
from shinywidgets import output_widget, render_widget
from shinywidgets._lifecycle import get_lifecycle


def live_sliders(session: Session) -> int:
    lifecycle = get_lifecycle(session.root_scope())
    return sum(
        isinstance(record.widget, ipywidgets.IntSlider)
        for record in lifecycle.records.values()
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

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render_widget
    def w():
        counter.get()
        return ipywidgets.IntSlider()

    # The old widget is collected only after the browser releases its display
    # lease (a round trip after the replacement attaches), so the count is
    # eventually consistent rather than flush-synchronous.
    @reactive.poll(lambda: live_sliders(session), 0.1)
    def widget_count() -> int:
        return live_sliders(session)

    @render.text
    def count():
        return f"renders={counter.get()} widgets={widget_count()}"


app_ui = ui.page_fluid(slider_ui("mod"))


def server(input, output, session):
    slider_server("mod")


app = App(app_ui, server)
