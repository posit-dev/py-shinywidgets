# Structure explorer: pick a representation/color scheme and click an atom for details.
# Bucket: template. Data: nglview's bundled rhodopsin structure (no network).
# Run: uv run shiny run gallery/template_structure_explorer.py
import nglview
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_nglview

ui.page_opts(fillable=True, title="Structure explorer")

REPRESENTATIONS = ["cartoon", "licorice", "spacefill", "surface"]
COLOR_SCHEMES = ["residueindex", "chainindex", "bfactor", "hydrophobicity"]

with ui.layout_sidebar():
    with ui.sidebar():
        ui.input_select("representation", "Representation", REPRESENTATIONS)
        ui.input_select("color_scheme", "Color scheme", COLOR_SCHEMES)
        ui.hr()
        ui.h5("Picked atom")

        @render.text
        def atom_info():
            picked = structure.read("picked")
            atom = picked.get("atom1") if picked else None
            if atom is None:
                return "Click an atom in the structure."
            return (
                f"{atom['resname']} {atom['resno']} chain {atom['chainname']}\n"
                f"atom: {atom['atomname']} (element {atom['element']})"
            )

    with ui.card(full_screen=True):

        @render_nglview
        def structure():
            view = nglview.show_file(
                nglview.datafiles.PDB, default_representation=False
            )
            view.add_representation("cartoon", color_scheme="residueindex")
            view.center()
            return view

        # Restyle in place: the camera position survives every change
        @reactive.effect
        def _restyle():
            view = structure.widget
            if view is None:
                return
            view.clear_representations()
            view.add_representation(
                input.representation(), color_scheme=input.color_scheme()
            )
