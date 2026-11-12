from __future__ import annotations

import pandas as pd
from shiny import App, ui
from shinywidgets import output_widget, render_itables

df = pd.DataFrame({"n": range(200), "letter": list("abcde") * 40})

app_ui = ui.page_fluid(
    ui.card(output_widget("short"), height="300px", id="short_card"),
)


def server(input, output, session):
    @render_itables
    def short():
        return df


app = App(app_ui, server)
