import pyvista as pv
from shiny.express import ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True  # required on a headless server

ui.page_opts(fillable=True)


@render_pyvista
def plot():
    pl = pv.Plotter()
    pl.add_mesh(pv.Sphere(), color="orange", show_edges=True)
    pl.view_isometric()
    return pl  # return the Plotter itself -- never call pl.show()
