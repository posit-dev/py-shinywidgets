from __future__ import annotations

import mols2grid
from shiny.express import ui
from shinywidgets import render_mols2grid

ui.page_opts(title="mols2grid: fields, styling, and transform", fillable=True)

mols = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)

with ui.card(full_screen=True):

    @render_mols2grid(
        subset=["NAME", "img", "SOL"],
        tooltip=["NAME", "SOL_classification"],
        sort_by="SOL",
        # transform only affects display text (in subset/tooltip fields), not
        # the underlying value used for sorting/selection
        transform={"SOL": lambda x: f"logS {x:.1f}"},
        border="2px solid #cfe2ff",
        background_color="#f8fbff",
        hover_color="#dbe9ff",
        gap=6,
        n_items_per_page=12,
    )
    def grid():
        return mols
