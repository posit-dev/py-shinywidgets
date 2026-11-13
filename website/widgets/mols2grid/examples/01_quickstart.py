from __future__ import annotations

import mols2grid
from shiny.express import ui
from shinywidgets import render_mols2grid

ui.page_opts(title="mols2grid quickstart", fillable=True)

mols = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)

with ui.card(full_screen=True):

    @render_mols2grid(subset=["ID"], tooltip=["ID", "NAME", "SOL"])
    def grid():
        return mols
