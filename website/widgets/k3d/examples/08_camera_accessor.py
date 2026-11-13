from __future__ import annotations

import k3d
import numpy as np
from shiny.express import render, ui
from shinywidgets import render_k3d

rng = np.random.default_rng(0)
xyz = (rng.normal(size=(4000, 3))).astype(np.float32)

ui.page_opts(title="camera() follows every orbit", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Drag to orbit, scroll to zoom")

        @render_k3d
        def scene():
            plot = k3d.plot()
            plot += k3d.points(xyz, point_size=0.08, color=0x4C78A8, shader="3d")
            return plot

    with ui.card():
        ui.card_header("scene.camera()")

        @render.code
        def camera_out():
            return "\n".join(f"{v:.2f}" for v in scene.camera())
