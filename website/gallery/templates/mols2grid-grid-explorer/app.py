# Title: Molecule grid explorer
# Summary: A clean, adaptable starting point for a mols2grid output: a
#     searchable grid plus a reactive readout of the checkbox selection, as a
#     DataFrame.
# Bucket: template
# Widgets: mols2grid
# Pattern: checkbox selection -> table
# Run: uv run shiny run app.py
# Data: mols2grid's bundled ESOL/Delaney solubility SDF (mols2grid.datafiles)
#
# Adapt by swapping MOLS for your own DataFrame (needs a SMILES column).
#
# Source: docs/widget-guides/mols2grid/gallery/template_grid_explorer.py

from __future__ import annotations

import mols2grid
import pandas as pd
from shiny import render
from shiny.express import ui
from shinywidgets import render_mols2grid

MOLS = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)
MOLS = MOLS[["SMILES", "ID", "SOL"]].rename(columns={"SOL": "LogS"})

ui.page_opts(title="Molecule grid explorer", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Solubility dataset")

        @render_mols2grid(subset=["ID"], tooltip=["ID", "LogS"])
        def grid():
            return MOLS

    with ui.card(full_screen=True):
        ui.card_header("Selected molecules")

        @render.data_frame
        def selected():
            idx = [int(k) for k in (grid.selected() or {})]
            return render.DataGrid(MOLS.loc[idx], width="100%")
