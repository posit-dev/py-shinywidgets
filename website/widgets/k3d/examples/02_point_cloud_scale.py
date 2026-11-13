from __future__ import annotations

import k3d
import numpy as np
from shiny.express import ui
from shinywidgets import render_k3d

N = 1_000_000
rng = np.random.default_rng(0)
xyz = (rng.normal(size=(N, 3)) * 3).astype(np.float32)
dist = np.linalg.norm(xyz, axis=1)

ui.page_opts(title=f"{N:,} points", fillable=True)


@render_k3d
def cloud():
    # An explicit camera (rather than auto-fit's zoomed-out default) composes
    # a tighter, more legible shot of the cluster.
    scene = k3d.plot(camera_auto_fit=False)
    scene.camera = [24, 19, 14, 0, 0, 0, 0, 0, 1]
    scene += k3d.points(
        xyz,
        point_size=0.03,
        shader="flat",
        attribute=dist,
        color_map=k3d.matplotlib_color_maps.Viridis,
        opacity=0.6,
    )
    return scene
