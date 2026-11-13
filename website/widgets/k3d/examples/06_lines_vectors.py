from __future__ import annotations

import k3d
import numpy as np
from shiny.express import ui
from shinywidgets import render_k3d


def lorenz_step(xyz: np.ndarray, s: float = 10, r: float = 28, b: float = 8 / 3) -> np.ndarray:
    x, y, z = xyz
    return np.array([s * (y - x), x * (r - z) - y, x * y - b * z])


dt, n = 0.01, 4000
path = np.empty((n, 3), dtype=np.float32)
path[0] = [0.1, 0.0, 0.0]
for i in range(1, n):
    path[i] = path[i - 1] + lorenz_step(path[i - 1]) * dt

# Local velocity (the Lorenz system's own derivative) at a few points, scaled
# down for display -- vectors show direction/speed along the trajectory.
sample = path[::400]
velocity = np.array([lorenz_step(p) for p in sample], dtype=np.float32) * 0.12

ui.page_opts(title="Lorenz attractor", fillable=True)


@render_k3d
def attractor():
    scene = k3d.plot()
    scene += k3d.line(path, color=0x1F77B4, shader="thick", width=0.3)
    scene += k3d.vectors(sample, velocity, color=0xE45756, head_size=4.0, line_width=0.6)
    return scene
