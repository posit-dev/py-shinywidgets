from __future__ import annotations

import pandas as pd
from shiny import App, ui
from shinywidgets import output_widget, render_perspective

df = pd.DataFrame({"id": range(100), "value": [i * 10 for i in range(100)]})

app_ui = ui.page_fillable(
    ui.card(output_widget("viewer", height="260px"), fill=False),
)


def server(input, output, session):
    @render_perspective
    def viewer():
        return df


app = App(app_ui, server)
