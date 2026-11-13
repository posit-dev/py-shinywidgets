from __future__ import annotations

import mols2grid
from shiny.express import ui
from shinywidgets import render_mols2grid

ui.page_opts(title="mols2grid: layout and sizing", fillable=True)

mols = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)

ui.card_header("Default: the grid sizes itself to its content; the page scrolls")
with ui.card():

    @render_mols2grid(subset=["ID"], n_items_per_page=12)
    def fills():
        return mols


ui.card_header(
    'iframe_height="150px" alone: the iframe is bounded, but the filling '
    "output container still stretches to the card -- empty space below"
)
with ui.card():

    @render_mols2grid(subset=["ID"], n_items_per_page=24, iframe_height="150px")
    def bounded():
        return mols


ui.card_header('iframe_height="150px" + fill=False: the output hugs its content too')
with ui.card():

    @render_mols2grid(
        subset=["ID"], n_items_per_page=24, iframe_height="150px", fill=False
    )
    def bounded_no_fill():
        return mols
