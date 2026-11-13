# Needs mdtraj to load the bundled trajectory: `uv run --with mdtraj shiny run ...`
import mdtraj
import nglview
import plotly.express as px
from shiny import reactive, req
from shiny.express import input, ui
from shinywidgets import render_nglview, render_plotly

ui.page_opts(fillable=True)

# A bundled 1 ns rhodopsin trajectory, 51 frames, 20 ps apart
traj = mdtraj.load(nglview.datafiles.XTC, top=nglview.datafiles.PDB)
ca = traj.topology.select("name CA")
rmsd = mdtraj.rmsd(traj, traj, 0, atom_indices=ca)

current_frame = reactive.value(0)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Trajectory")

        @render_nglview
        def structure():
            return nglview.show_mdtraj(traj)

    with ui.card(full_screen=True):
        ui.card_header("RMSD to frame 0 (click a point to jump there)")

        @render_plotly
        def rmsd_plot():
            with reactive.isolate():
                start = current_frame.get()
            fig = px.line(
                x=list(range(len(rmsd))), y=rmsd, markers=True,
                labels={"x": "Frame", "y": "C-alpha RMSD (nm)"},
            )
            fig.add_vline(x=start, line_dash="dash", line_color="orange")
            return fig

ui.input_slider("frame", "Frame", min=0, max=traj.n_frames - 1, value=0, animate=True)


# The slider drives the shared frame value ...
@reactive.effect
def _slider_to_frame():
    current_frame.set(input.frame())


# ... and so does clicking a point on the RMSD plot, via plotly's clicked()
# accessor, keeping the slider in sync
@reactive.effect
def _chart_to_frame():
    pts = rmsd_plot.clicked()
    req(pts is not None)
    frame = int(pts["x"].iloc[0])
    current_frame.set(frame)
    ui.update_slider("frame", value=frame)


# Both the viewer and the plot's marker update in place: no re-render, so
# zoom/selection on the plot and the camera on the viewer are preserved
@reactive.effect
def _move_viewer():
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
