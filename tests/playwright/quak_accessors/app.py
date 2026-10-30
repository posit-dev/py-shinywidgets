from __future__ import annotations

import pandas as pd
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_quak

df = pd.DataFrame(
    {
        "id": range(500),
        "group": ["a", "b", "c", "d"] * 125,
        "value": [(i * 37) % 101 for i in range(500)],
    }
)

app_ui = ui.page_fluid(
    ui.output_text("sql"),
    ui.output_text("n_rows"),
    ui.output_text("n_sql_reads"),
    ui.card(output_widget("short"), id="short_card", height="450px"),
)


def server(input, output, session):
    # Counts executions of the `sql` output (the debounce probe)
    read_count = reactive.value(0)

    @render_quak
    def short():
        return df

    @render.text
    def sql():
        with reactive.isolate():
            read_count.set(read_count() + 1)
        return short.sql()

    @render.text
    def n_rows():
        return str(len(short.data().df()))

    @render.text
    def n_sql_reads():
        return str(read_count())


app = App(app_ui, server)
