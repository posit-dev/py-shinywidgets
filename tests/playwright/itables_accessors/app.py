from __future__ import annotations

import pandas as pd
from itables.widget import ITable
from shiny import App, render, ui
from shinywidgets import output_widget, render_itables

df = pd.DataFrame({"n": range(50), "s": [f"item {i}" for i in range(50)]})

app_ui = ui.page_fluid(
    output_widget("table"),
    ui.output_text("sel"),
)


def server(input, output, session):
    @render_itables
    def table():
        return ITable(df, select=True)

    @render.text
    def sel():
        return str(table.selected_rows())


app = App(app_ui, server)
