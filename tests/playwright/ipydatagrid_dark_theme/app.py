from __future__ import annotations

import pandas as pd
from shiny import App, ui
from shinywidgets import output_widget, render_ipydatagrid

app_ui = ui.page_fluid(
    ui.input_dark_mode(mode="dark"),
    output_widget("grid"),
)


def server(input, output, session):
    @render_ipydatagrid
    def grid():
        return pd.DataFrame({"a": range(20), "b": range(100, 120)})


app = App(app_ui, server)
