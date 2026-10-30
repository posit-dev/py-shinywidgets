from __future__ import annotations

import pandas as pd
from ipydatagrid import DataGrid
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipydatagrid

df = pd.DataFrame(
    {
        "a": range(20),
        "b": [f"v{i}" for i in range(20)],
        "c": [i * 1.5 for i in range(20)],
    }
)

df2 = pd.DataFrame(
    {
        "a": range(100, 120),
        "b": [f"w{i}" for i in range(20)],
        "c": [i * 2.5 for i in range(20)],
    }
)

app_ui = ui.page_fluid(
    ui.input_action_button("replace", "Replace data"),
    output_widget("grid", height="500px"),
    ui.output_text("sels"),
    ui.output_text("click"),
    ui.output_text("edit"),
    ui.output_text("vis"),
)


def server(input, output, session):
    @render_ipydatagrid
    def grid():
        return DataGrid(df, selection_mode="row", editable=True)

    @reactive.effect
    @reactive.event(input.replace)
    def _():
        grid.widget.data = df2

    @render.text
    def sels():
        return str(grid.selections())

    @render.text
    def click():
        return str(grid.cell_clicked())

    @render.text
    def edit():
        return str(grid.cell_edited())

    @render.text
    def vis():
        return ",".join(map(str, grid.visible_data()["a"].tolist()))


app = App(app_ui, server)
