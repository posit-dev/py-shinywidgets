import numpy as np
import pyvista as pv
from shiny.express import ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True)

# A synthetic vortex field: direction and speed, sampled on a coarse grid
x, y = np.mgrid[-5:5:21j, -5:5:21j]
z = np.zeros_like(x)
points = pv.PolyData(np.c_[x.ravel(), y.ravel(), z.ravel()])
r = np.sqrt(x.ravel() ** 2 + y.ravel() ** 2)
r_safe = np.clip(r, 0.6, None)  # avoid a singularity at the core
speed = 3 / (r_safe + 1)  # fastest near the core, decaying outward
vectors = speed[:, None] * np.c_[-y.ravel() / r_safe, x.ravel() / r_safe, np.zeros_like(r)]
points["vectors"] = vectors
points["speed"] = speed


@render_pyvista
def plot():
    pl = pv.Plotter()
    arrows = points.glyph(orient="vectors", scale="speed", factor=1.0)
    pl.add_mesh(arrows, scalars="speed", cmap="viridis", show_scalar_bar=False)
    pl.view_isometric()
    return pl
