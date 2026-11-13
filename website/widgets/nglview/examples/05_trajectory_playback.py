# Needs mdtraj to load the bundled trajectory: `uv run --with mdtraj shiny run ...`
# (or `pip install mdtraj`; MDAnalysis works too, via nglview.show_mdanalysis()).
import mdtraj
import nglview
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_nglview

ui.page_opts(fillable=True)

# A bundled 1 ns rhodopsin trajectory, 51 frames, 20 ps apart
traj = mdtraj.load(nglview.datafiles.XTC, top=nglview.datafiles.PDB)

ui.input_slider("frame", "Frame", min=0, max=traj.n_frames - 1, value=0, animate=True)

with ui.card(full_screen=True):

    @render_nglview
    def structure():
        return nglview.show_mdtraj(traj)

    # `frame` is a synced trait: setting it in place sends only the new
    # coordinates, not the whole structure again
    @reactive.effect
    def _scrub():
        view = structure.widget
        if view is not None:
            view.frame = input.frame()
