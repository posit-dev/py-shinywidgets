# PyVista isosurface explorer -- template bucket
# A small, adaptable starting point: a threshold slider re-renders an
# isosurface extracted from a scalar volume, paired with stats computed in
# Python from the same mesh. Swap `load_volume()` for your own ImageData/
# RectilinearGrid (CT/MRI scans, simulation output, ...) and keep the rest.
# Run: shiny run gallery/template_isosurface_explorer.py
# Data: pyvista.examples.download_knee_full() (a public-domain CT scan,
# downloaded once and cached locally by pyvista)

import pyvista as pv
from pyvista import examples
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True, title="Isosurface explorer")
ui.input_slider("threshold", "Threshold", 20, 200, 80, step=10)


@reactive.calc
def volume():
    # Loaded once per process (cached by @reactive.calc across re-renders);
    # downsample large volumes before contouring to keep the exported scene
    # (and the triangle count) manageable
    v = examples.download_knee_full()
    dims = v.dimensions
    return v.extract_subset((0, dims[0] - 1, 0, dims[1] - 1, 0, dims[2] - 1), (3, 3, 3))


@reactive.calc
def isosurface():
    return volume().contour([input.threshold()])


with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):

        @render_pyvista
        def plot():
            pl = pv.Plotter()
            pl.add_mesh(isosurface(), color="ivory", smooth_shading=True)
            pl.view_isometric()
            return pl

    with ui.card():
        ui.card_header("Surface stats")

        @render.code
        def stats():
            mesh = isosurface()
            return (
                f"{mesh.n_points:,} points\n"
                f"{mesh.n_cells:,} triangles\n"
                f"{mesh.area:,.0f} units^2 surface area"
            )
