from __future__ import annotations

import mols2grid
from shiny.express import render, ui
from shinywidgets import render_mols2grid

ui.page_opts(title="mols2grid clicked() accessor", fillable=True)
ui.tags.style("pre { white-space: pre-wrap; overflow-wrap: anywhere; }")

mols = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_mols2grid(
            clicks=True, subset=["ID"], tooltip=["ID", "SOL"], n_items_per_page=12
        )
        def grid():
            return mols

    with ui.card():
        ui.card_header("grid.clicked()")

        @render.code
        def clicked():
            # None until a molecule's image is clicked (a distinct gesture
            # from the selection checkbox); keeps its value across re-renders
            # until the user clicks the new grid. The row also carries an
            # "img" key (the cell's raw SVG) -- drop it unless you actually
            # want the markup.
            row = grid.clicked()
            if row is None:
                return "No click yet"
            return str({k: v for k, v in row.items() if k != "img"})
