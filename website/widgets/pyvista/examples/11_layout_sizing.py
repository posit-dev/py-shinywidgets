import pyvista as pv
from pyvista import examples
from shiny.express import ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True)


def make_plotter():
    pl = pv.Plotter()
    pl.add_mesh(examples.load_random_hills(), scalars="Elevation", cmap="terrain")
    pl.view_isometric()
    return pl


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Fills its card (default)")

        @render_pyvista
        def fills():
            return make_plotter()

    with ui.card():
        ui.card_header("Explicit height")

        @render_pyvista(height="250px")
        def fixed_height():
            return make_plotter()
