import numpy as np
import pyvista as pv
from shiny import App, ui
from shinywidgets import output_widget, render_pyvista

# pyvista needs off-screen rendering on a (headless) server
pv.OFF_SCREEN = True

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_slider("freq", "Wave frequency", 1, 8, 3),
            ui.input_slider("res", "Mesh resolution", 20, 200, 80),
        ),
        output_widget("plot"),
    )
)


def server(input, output, session):
    @render_pyvista
    def plot():
        # A synthetic "wavy" surface, recomputed on every slider change
        x = np.linspace(-2, 2, input.res())
        y = np.linspace(-2, 2, input.res())
        xx, yy = np.meshgrid(x, y)
        zz = np.sin(input.freq() * (xx**2 + yy**2))
        grid = pv.StructuredGrid(xx, yy, zz)
        pl = pv.Plotter()
        pl.add_mesh(grid, scalars=zz.ravel(), cmap="viridis", show_edges=False)
        pl.view_isometric()
        return pl


app = App(app_ui, server)
