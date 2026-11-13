import pyvista as pv
from pyvista import examples
from shiny.express import ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True)

# A classic CFD dataset: airflow in a kitchen, plus the room's geometry
# (walls, cabinets, a door) as a separate multi-block for context
flow = examples.download_kitchen()
flow.set_active_vectors("velocity")
room = examples.download_kitchen(split=True).combine()

streamlines = flow.streamlines(
    "velocity", source_center=(0.08, 3, 0.7), source_radius=0.75, n_points=15, max_length=200.0
)


@render_pyvista
def plot():
    pl = pv.Plotter()
    pl.add_mesh(room, color="lightgray", opacity=0.25, show_edges=True, edge_color="gray")
    pl.add_mesh(
        streamlines.tube(radius=0.03), scalars="velocity", cmap="plasma", show_scalar_bar=False
    )
    pl.camera_position = [(13, -8, 9), (3.5, 2.5, 1), (0, 0, 1)]
    return pl
