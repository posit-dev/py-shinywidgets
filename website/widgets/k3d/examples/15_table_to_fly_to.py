# Pairs with: itables, reactable (swap render.data_frame for either).
from __future__ import annotations

import k3d
import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_k3d

landmarks = pd.DataFrame(
    {
        "name": ["Alpha", "Bravo", "Charlie", "Delta", "Echo"],
        "x": [3.0, -4.0, 1.0, -2.0, 4.0],
        "y": [2.0, 3.0, -4.0, -3.0, -1.0],
        "z": [1.0, -1.0, 2.0, -2.0, 3.0],
    }
)
xyz = landmarks[["x", "y", "z"]].to_numpy(np.float32)
HOME = [12, -10, 8, 0, 0, 0, 0, 0, 1]

ui.page_opts(title="Select a row, fly the camera there", fillable=True)

with ui.layout_columns(col_widths=[5, 7]):
    with ui.card():
        ui.card_header("Pick a landmark")

        @render.data_frame
        def table():
            return render.DataGrid(landmarks, selection_mode="row")

    with ui.card(full_screen=True):
        ui.card_header("Flies there, and highlights it")

        @render_k3d
        def scene():
            plot = k3d.plot(camera_auto_fit=False)
            plot.camera = HOME
            plot += k3d.points(xyz, point_size=0.3, color=0x4C78A8, shader="3d")
            plot += k3d.points(xyz[:1], point_size=0.45, color=0xE45756, visible=False)
            return plot


@reactive.effect
def _fly_to_selection():
    sel = table.cell_selection()["rows"]
    if not sel:
        return
    idx = sel[0]
    x, y, z = (float(v) for v in xyz[idx])
    scene.widget.camera = [x + 3, y - 3, z + 2, x, y, z, 0, 0, 1]
    highlight = scene.widget.objects[1]
    highlight.positions = xyz[idx : idx + 1]
    highlight.visible = True
