import pyvista as pv
from pyvista import examples
from shiny.express import ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True)

# A real CT scan (a knee), downsampled 3x per axis to keep the extracted
# surface (and the exported scene) a reasonable size
volume = examples.download_knee_full()
volume = volume.extract_subset(
    (0, volume.dimensions[0] - 1, 0, volume.dimensions[1] - 1, 0, volume.dimensions[2] - 1),
    (3, 3, 3),
)


@render_pyvista
def plot():
    pl = pv.Plotter()
    bone = volume.contour([80])  # marching cubes at a bone-density threshold
    pl.add_mesh(bone, color="ivory", smooth_shading=True)
    pl.view_isometric()
    return pl
