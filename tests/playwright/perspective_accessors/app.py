from __future__ import annotations

import pandas as pd
from shiny import App, render, ui
from shinywidgets import output_widget, render_perspective

df = pd.DataFrame(
    {
        "id": range(30),
        "category": [["A", "B", "C"][i % 3] for i in range(30)],
        "value": [i * 10 for i in range(30)],
    }
)

app_ui = ui.page_fluid(
    ui.output_text("filter_out"),
    ui.output_text("config_out"),
    output_widget("grid"),
)


def server(input, output, session):
    @render_perspective
    def grid():
        return df

    @render.text
    def filter_out():
        return str(grid.filter())

    @render.text
    def config_out():
        cfg = grid.view_config()
        return f"sort={cfg['sort']} group_by={cfg['group_by']}"


app = App(app_ui, server)
