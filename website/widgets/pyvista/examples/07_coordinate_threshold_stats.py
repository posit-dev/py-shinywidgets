import pyvista as pv
from pyvista import examples
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True)
ui.input_slider("threshold", "Bone-density threshold", 20, 200, 80, step=10)

with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):

        @reactive.calc
        def volume():
            # Downloaded and downsampled once per process, not per re-render
            v = examples.download_knee_full()
            dims = v.dimensions
            return v.extract_subset((0, dims[0] - 1, 0, dims[1] - 1, 0, dims[2] - 1), (3, 3, 3))

        @reactive.calc
        def isosurface():
            return volume().contour([input.threshold()])

        @render_pyvista
        def plot():
            pl = pv.Plotter()
            pl.add_mesh(isosurface(), color="ivory", smooth_shading=True)
            pl.view_isometric()
            return pl

    with ui.card():
        ui.card_header("Computed from the same mesh, in Python")

        @render.code
        def stats():
            mesh = isosurface()
            return f"{mesh.n_points:,} points\n{mesh.n_cells:,} triangles\n{mesh.area:,.0f} units^2 surface area"
