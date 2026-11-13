import nglview
from shiny.express import input, ui
from shinywidgets import render_nglview

ui.page_opts(fillable=True)

ui.input_select(
    "source",
    "Structure source",
    {
        "bundled": "Bundled file (nglview.datafiles.PDB, no network)",
        "rcsb": "Fetched by the browser from RCSB (4HHB, hemoglobin)",
    },
)

with ui.card(full_screen=True):

    @render_nglview
    def structure():
        if input.source() == "bundled":
            # Read on the server; good for files you already have locally
            return nglview.show_file(nglview.datafiles.PDB)
        # show_url() queues a loadFile the *browser* fetches directly, so the
        # server never downloads the structure. Prefer this (or show_file/
        # show_text) over show_pdbid(), which blocks the server on urlopen().
        return nglview.show_url("https://files.rcsb.org/download/4HHB.cif")
