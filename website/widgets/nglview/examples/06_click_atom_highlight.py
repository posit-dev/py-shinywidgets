import nglview
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_nglview

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_nglview
        def structure():
            view = nglview.show_file(
                nglview.datafiles.PDB, default_representation=False
            )
            view.add_representation("cartoon", color="lightgrey")
            view.add_representation("ball+stick", selection="hetero")
            view.center()
            return view

    with ui.card():
        ui.card_header("Picked atom")

        @render.text
        def atom_info():
            picked = structure.read("picked")
            atom = picked.get("atom1") if picked else None
            if atom is None:
                return "Click an atom in the structure."
            return (
                f"{atom['resname']} {atom['resno']} chain {atom['chainname']}\n"
                f"atom: {atom['atomname']} (element {atom['element']})\n"
                f"b-factor: {atom['bfactor']:.1f}"
            )

    # Highlight the clicked residue in place, on top of the cartoon
    @reactive.effect
    def _highlight_picked():
        view = structure.widget
        if view is None:
            return
        picked = structure.read("picked")
        atom = picked.get("atom1") if picked else None
        view.remove_spacefill()
        if atom is not None:
            view.add_representation(
                "spacefill", selection=str(atom["resno"]), color="orange"
            )
