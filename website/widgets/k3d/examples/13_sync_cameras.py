# camera() isn't just for display -- it can drive a second view directly, so
# two k3d plots stay in lockstep as you orbit either one. Try panning the
# left plot and watch the right one (lit from the opposite side) follow.
from __future__ import annotations

import k3d
import numpy as np
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_k3d

rng = np.random.default_rng(0)
xyz = (rng.normal(size=(4000, 3))).astype(np.float32)
dist = np.linalg.norm(xyz, axis=1)
# Give both plots the same starting camera explicitly, rather than relying on
# auto-fit: camera() seeds its first value very early (before either plot's
# comm has opened), so the very first copy from left to right can be dropped
# (see Gotchas). Starting both plots alike means that dropped first copy is
# never visible -- every copy after a real orbit lands normally.
START = [10, -8, 6, 0, 0, 0, 0, 0, 1]

ui.page_opts(title="Two views, one camera", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Drag to orbit")

        @render_k3d
        def left():
            plot = k3d.plot(camera_auto_fit=False)
            plot.camera = START
            plot += k3d.points(xyz, point_size=0.08, attribute=dist, color_map=k3d.matplotlib_color_maps.Viridis)
            return plot

    with ui.card(full_screen=True):
        ui.card_header("Follows the left plot's camera")

        @render_k3d
        def right():
            plot = k3d.plot(camera_auto_fit=False)
            plot.camera = START
            plot += k3d.points(xyz, point_size=0.08, attribute=dist, color_map=k3d.matplotlib_color_maps.Plasma)
            return plot


@reactive.effect
def _sync():
    camera = left.camera()
    with reactive.isolate():
        right.widget.camera = camera
