from __future__ import annotations

import pandas as pd
import quak
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_quak

df = pd.DataFrame(
    {
        "id": range(500),
        "group": ["a", "b", "c", "d"] * 125,
        "value": [(i * 37) % 101 for i in range(500)],
    }
)

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("sql"),
    ui.card(output_widget("short"), id="short_card", height="450px"),
    ui.card(output_widget("tall"), id="tall_card", height="800px"),
    ui.card(output_widget("fixed", height="300px"), id="fixed_card"),
    ui.card(output_widget("layout"), id="layout_card"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_quak
    def short():
        counter.get()
        return df

    @render_quak
    def tall():
        return df

    @render_quak
    def fixed():
        return df

    @render_quak
    def layout():
        widget = quak.Widget(df)
        widget.layout.height = "260px"
        return widget

    @render.text
    def sql():
        return reactive_read(short.widget, "sql")


app = App(app_ui, server)
