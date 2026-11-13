from __future__ import annotations

import mols2grid
from shiny.express import render, ui
from shinywidgets import render_mols2grid

ui.page_opts(title="mols2grid selected() accessor", fillable=True)

mols = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_mols2grid(subset=["ID"], tooltip=["ID", "SOL"], n_items_per_page=12)
        def grid():
            return mols

    with ui.card():
        ui.card_header("grid.selected()")

        @render.code
        def selected():
            # {} once the grid has rendered and nothing is checked yet; each
            # checkbox toggle re-runs this (positional row index -> SMILES)
            return str(grid.selected())
