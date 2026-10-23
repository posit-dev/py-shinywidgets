from __future__ import annotations

import pandas as pd
from shiny import App, ui
from shinywidgets import output_widget, render_itables

app_ui = ui.page_fluid(
    ui.input_dark_mode(mode="dark"),
    ui.card(output_widget("table")),
)


def server(input, output, session):
    @render_itables
    def table():
        return pd.DataFrame({"n": range(20)})


app = App(app_ui, server)
