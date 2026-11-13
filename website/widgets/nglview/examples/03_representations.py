import nglview
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_nglview

ui.page_opts(fillable=True)

REPRESENTATIONS = ["cartoon", "licorice", "spacefill", "surface"]
COLOR_SCHEMES = ["residueindex", "chainindex", "bfactor", "hydrophobicity"]

with ui.sidebar():
    ui.input_select("representation", "Representation", REPRESENTATIONS)
    ui.input_select("color_scheme", "Color scheme", COLOR_SCHEMES)

with ui.card(full_screen=True):

    @render_nglview
    def structure():
        view = nglview.show_file(
            nglview.datafiles.PDB, default_representation=False
        )
        view.add_representation("cartoon", color_scheme="residueindex")
        view.center()
        return view

    # Restyle the already-rendered viewer in place instead of re-rendering:
    # the camera position and zoom survive, and the structure file isn't
    # re-sent to the browser
    @reactive.effect
    def _restyle():
        view = structure.widget
        if view is None:
            return
        view.clear_representations()
        view.add_representation(
            input.representation(), color_scheme=input.color_scheme()
        )
