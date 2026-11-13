from __future__ import annotations

import k3d
import numpy as np
from shiny.express import ui
from shinywidgets import render_k3d

n = 64
lin = np.linspace(-1, 1, n, dtype=np.float32)
x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
blobs = [(-0.3, -0.2, 0.1, 0.25), (0.3, 0.2, -0.1, 0.3), (0.0, 0.4, 0.3, 0.2)]
density = np.zeros((n, n, n), dtype=np.float32)
for cx, cy, cz, spread in blobs:
    density += np.exp(-((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2) / (2 * spread**2))

ui.page_opts(title="Volumetric density field", fillable=True)


@render_k3d
def nebula():
    scene = k3d.plot()
    scene += k3d.volume(
        density,
        color_map=k3d.matplotlib_color_maps.Plasma,
        color_range=[0.1, density.max()],
        alpha_coef=25,
    )
    return scene
