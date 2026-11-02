from __future__ import annotations

import pandas as pd
from shiny import App, render, ui
from shinywidgets import output_widget, render_mols2grid

DF = pd.DataFrame(
    {
        "SMILES": ["CCO", "c1ccccc1", "CCC(C)CC"],
        "ID": ["mol-0", "mol-1", "mol-2"],
    }
)

app_ui = ui.page_fluid(
    output_widget("grid"),
    ui.output_text("selected"),
    ui.output_text("clicked"),
)


def server(input, output, session):
    @render_mols2grid(clicks=True, subset=["ID"], tooltip=["ID"])
    def grid():
        return DF

    @render.text
    def selected():
        return str(grid.selection())

    @render.text
    def clicked():
        row = grid.clicked()
        return "" if row is None else str(row["ID"])


app = App(app_ui, server)
