import nglview
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_nglview

ui.page_opts(fillable=True)

ui.input_slider("residues", "Highlight residues", min=1, max=348, value=(260, 265))

with ui.card(full_screen=True):
    ui.card_header("Rhodopsin (1U19): highlight a residue range")

    @render_nglview
    def structure():
        view = nglview.show_file(
            nglview.datafiles.PDB, default_representation=False
        )
        view.add_representation("cartoon", color="lightgrey")
        view.center()
        return view

    # NGL's selection language ("262", "260-265", "LRT", "protein", ...) picks
    # out atoms by residue number, name, or keyword. A distinct representation
    # type (spacefill) for the highlight means remove_spacefill() only clears
    # it, leaving the cartoon representation untouched.
    @reactive.effect
    def _highlight():
        view = structure.widget
        if view is None:
            return
        lo, hi = input.residues()
        view.remove_spacefill()
        view.add_representation("spacefill", selection=f"{lo}-{hi}", color="red")
