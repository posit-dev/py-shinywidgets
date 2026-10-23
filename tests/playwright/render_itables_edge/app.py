from __future__ import annotations

import pandas as pd
from ipywidgets import VBox
from itables.widget import ITable
from shiny import App, ui
from shinywidgets import output_widget, render_itables, render_widget

df = pd.DataFrame({"n": range(200), "letter": list("abcde") * 40})

app_ui = ui.page_fluid(
    ui.card(output_widget("scrolly", height="400px"), id="scrolly_card"),
    ui.card(output_widget("nested"), height="40vh", id="nested_card"),
)


def server(input, output, session):
    @render_itables
    def scrolly():
        return ITable(df, scrollY="150px", scrollX=True)

    @render_widget
    def nested():
        return VBox([ITable(df)])


app = App(app_ui, server)
