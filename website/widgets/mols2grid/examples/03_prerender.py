from __future__ import annotations

import mols2grid
from shiny.express import ui
from shinywidgets import render_mols2grid

ui.page_opts(title="mols2grid with prerender=True", fillable=True)

mols = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)

with ui.card(full_screen=True):

    # prerender=True draws every depiction server-side with RDKit and embeds
    # the images directly, so the browser never redraws them -- but the page
    # still loads RDKit MinimalLib (it powers the SMARTS search box) plus
    # jQuery, Bootstrap, and list.js from CDNs, so this does not make the grid
    # work offline, and substructure-match highlighting is unavailable (it
    # needs per-cell client-side redraws).
    @render_mols2grid(subset=["ID"], tooltip=["ID", "SOL"], prerender=True)
    def grid():
        return mols
