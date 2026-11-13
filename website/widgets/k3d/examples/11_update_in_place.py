from __future__ import annotations

import k3d
import numpy as np
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_k3d

rng = np.random.default_rng(0)
xyz = (rng.normal(size=(20_000, 3))).astype(np.float32)

ui.page_opts(title="Resize points without rebuilding the scene", fillable=True)
ui.input_slider("point_size", "Point size", min=0.02, max=0.3, value=0.08)


@render_k3d
def scene():
    # The render function never reads point_size, so this never re-runs:
    # orbit/zoom survive every slider move.
    plot = k3d.plot()
    plot += k3d.points(xyz, point_size=0.08, color=0x4C78A8, shader="3d")
    return plot


@reactive.effect
def _resize():
    scene.widget.objects[0].point_size = input.point_size()
