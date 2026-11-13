import pyvista as pv
from pyvista import examples
from shiny.express import ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True)

# A synthetic rolling-hills terrain, bundled with pyvista -- no download
hills = examples.load_random_hills()


@render_pyvista
def plot():
    pl = pv.Plotter()
    pl.add_mesh(hills, scalars="Elevation", cmap="terrain", show_scalar_bar=True)
    pl.view_isometric()
    return pl
