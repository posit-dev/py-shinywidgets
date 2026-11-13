from __future__ import annotations

import k3d
import numpy as np
from shiny.express import ui
from shinywidgets import render_k3d

n = 80
lin = np.linspace(-2, 2, n, dtype=np.float32)
x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
major_radius, minor_radius = 1.0, 0.4
field = (np.sqrt(x**2 + y**2) - major_radius) ** 2 + z**2 - minor_radius**2

ui.page_opts(title="An isosurface, from a scalar field", fillable=True)


@render_k3d
def torus():
    scene = k3d.plot()
    scene += k3d.marching_cubes(
        field, level=0.0, color=0x2E86AB, flat_shading=False
    )
    return scene
