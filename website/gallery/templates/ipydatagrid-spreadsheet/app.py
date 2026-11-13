# Title: Spreadsheet
# Summary: An editable, cell-selectable grid with a status bar that reports
#     Count/Sum/Average/Min/Max for whatever rectangle of cells you drag over,
#     plus a live edit log. Swap in your own DataFrame and go.
# Bucket: template
# Widgets: ipydatagrid
# Pattern: cell selection -> live stats
# Run: uv run shiny run app.py
# Data: synthesized in-line (numpy)
#
# Source: docs/widget-guides/ipydatagrid/gallery/template_spreadsheet.py

import numpy as np
import pandas as pd
from ipydatagrid import DataGrid
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_ipydatagrid

rng = np.random.default_rng(7)
df = pd.DataFrame(
    rng.integers(0, 100, (12, 5)), columns=[f"Q{i + 1}" for i in range(5)]
)

ui.page_opts(fillable=True, title="Spreadsheet template")

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Drag to select a block; double-click a cell to edit")

        @render_ipydatagrid
        def grid():
            return DataGrid(df, selection_mode="cell", editable=True)

    with ui.card():
        ui.card_header("Status bar")

        @render.ui
        def status():
            sels = grid.selected()
            if not sels:
                return "Select a block of cells."
            vis = grid.visible_data()
            block = np.concatenate(
                [
                    vis.iloc[s["r1"] : s["r2"] + 1, s["c1"] : s["c2"] + 1]
                    .to_numpy()
                    .ravel()
                    for s in sels
                ]
            )
            return ui.TagList(
                ui.p(f"Count {block.size} · Sum {block.sum()}"),
                ui.p(
                    f"Average {block.mean():.1f} · Min {block.min()} · "
                    f"Max {block.max()}"
                ),
            )

        ui.card_header("Last edit")

        @render.text
        def last_edit():
            edit = grid.edited_cell()
            req(edit)
            return f"row {edit['row']}, {edit['column']} -> {edit['value']}"
