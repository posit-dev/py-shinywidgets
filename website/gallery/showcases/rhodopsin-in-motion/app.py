# Rhodopsin in motion: scrub or click through an MD trajectory, linked to an
# RMSD chart, with click-to-inspect and residue highlighting.
# Bucket: showcase. Data: nglview's bundled rhodopsin trajectory (no network).
# Run: uv run --with mdtraj shiny run app.py
import mdtraj
import nglview
import plotly.express as px
from shiny import reactive, req
from shiny.express import input, render, ui
from shinywidgets import render_nglview, render_plotly

ui.page_opts(fillable=True, title="Rhodopsin in motion")

# A bundled 1 ns rhodopsin trajectory, 51 frames, 20 ps apart
traj = mdtraj.load(nglview.datafiles.XTC, top=nglview.datafiles.PDB)
ca = traj.topology.select("name CA")
rmsd = mdtraj.rmsd(traj, traj, 0, atom_indices=ca)

current_frame = reactive.value(0)

with ui.layout_sidebar():
    with ui.sidebar(width=300):
        ui.input_slider(
            "frame", "Frame", min=0, max=traj.n_frames - 1, value=0, animate=True
        )
        ui.input_select(
            "representation",
            "Representation",
            ["cartoon", "licorice", "spacefill", "surface"],
        )
        ui.input_slider("residues", "Highlight residues", min=1, max=348, value=(260, 265))
        ui.hr()
        ui.h5("Picked atom")

        @render.text
        def atom_info():
            picked = structure.read("picked")
            atom = picked.get("atom1") if picked else None
            if atom is None:
                return "Click an atom in the structure."
            return f"{atom['resname']} {atom['resno']} chain {atom['chainname']}"

    with ui.layout_columns():
        with ui.card(full_screen=True):
            ui.card_header("Trajectory")

            @render_nglview
            def structure():
                view = nglview.show_mdtraj(traj, default_representation=False)
                view.add_representation("cartoon", color="lightgrey")
                view.center()
                return view

        with ui.card(full_screen=True):
            ui.card_header("C-alpha RMSD to frame 0 (click a point to jump there)")

            @render_plotly
            def rmsd_plot():
                with reactive.isolate():
                    start = current_frame.get()
                fig = px.line(
                    x=list(range(len(rmsd))), y=rmsd, markers=True,
                    labels={"x": "Frame", "y": "RMSD (nm)"},
                )
                fig.add_vline(x=start, line_dash="dash", line_color="orange")
                return fig


# The slider, and clicking the chart, both drive the one shared frame value
@reactive.effect
def _slider_to_frame():
    current_frame.set(input.frame())


@reactive.effect
def _chart_to_frame():
    pts = rmsd_plot.clicked()
    req(pts is not None)
    frame = int(pts["x"].iloc[0])
    current_frame.set(frame)
    ui.update_slider("frame", value=frame)


# Everything below updates in place: no re-render, so the camera and the
# chart's zoom are untouched by playback or restyling
@reactive.effect
def _move_viewer_frame():
    view = structure.widget
    if view is not None:
        view.frame = current_frame()


@reactive.effect
def _move_marker():
    fig = rmsd_plot.widget
    if fig is not None:
        frame = current_frame()
        with fig.batch_update():
            fig.layout.shapes[0].x0 = frame
            fig.layout.shapes[0].x1 = frame


# One effect for both the representation and the highlight, since both
# rebuild the representation list and would otherwise race against each other
@reactive.effect
def _restyle_and_highlight():
    view = structure.widget
    if view is None:
        return
    lo, hi = input.residues()
    view.clear_representations()
    view.add_representation(input.representation(), color="lightgrey")
    view.add_representation("spacefill", selection=f"{lo}-{hi}", color="orange")
