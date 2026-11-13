import nglview
from shiny.express import ui
from shinywidgets import render_nglview

ui.page_opts(fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Rhodopsin (PDB 1U19)")

    @render_nglview
    def structure():
        # nglview ships a few structures for examples/tests; no network needed
        view = nglview.show_file(nglview.datafiles.PDB)
        view.center()
        view.control.zoom(0.3)
        return view
