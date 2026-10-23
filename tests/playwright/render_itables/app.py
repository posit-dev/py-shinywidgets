from __future__ import annotations

import pandas as pd
from itables.widget import ITable
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_itables

df = pd.DataFrame({"n": range(200), "letter": list("abcde") * 40})

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.card(output_widget("table"), height="50vh", id="fill_card"),
    ui.card(output_widget("explicit", height="250px"), id="explicit_card"),
    ui.output_text("selected"),
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

    @render_itables
    def table():
        counter.get()
        return ITable(df, select=True)

    @render_itables
    def explicit():
        return df

    @render.text
    def selected():
        return str(reactive_read(table.widget, "selected_rows"))


app = App(app_ui, server)
