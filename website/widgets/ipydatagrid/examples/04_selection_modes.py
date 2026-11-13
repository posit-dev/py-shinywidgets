import numpy as np
import pandas as pd
from ipydatagrid import DataGrid
from shiny.express import input, render, ui
from shinywidgets import render_ipydatagrid

rng = np.random.default_rng(2)
scores = pd.DataFrame(
    rng.integers(50, 100, (10, 4)), columns=["Q1", "Q2", "Q3", "Q4"]
)

ui.page_opts(fillable=True)
ui.input_radio_buttons(
    "mode", "Selection mode", choices=["cell", "row", "column"], selected="cell"
)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Drag to select; the mode changes what a drag selects")

        @render_ipydatagrid
        def grid():
            return DataGrid(scores, selection_mode=input.mode())

    with ui.card():
        ui.card_header("Selection status bar")

        @render.ui
        def status():
            sels = grid.selected()
            if not sels:
                return "Nothing selected."
            vis = grid.visible_data()
            values = [
                vis.iloc[s["r1"] : s["r2"] + 1, s["c1"] : s["c2"] + 1].to_numpy()
                for s in sels
            ]
            flat = np.concatenate([v.ravel() for v in values])
            return ui.TagList(
                ui.p(f"Count {flat.size} · Sum {flat.sum()}"),
                ui.p(f"Average {flat.mean():.1f} · Min {flat.min()} · Max {flat.max()}"),
            )
