# k3d has no clicked() accessor (picking needs mode="callback", a user-visible
# change to the plot's interaction mode) -- wire k3d's own click_callback to a
# reactive.value instead.
from __future__ import annotations

import k3d
import numpy as np
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_k3d

rng = np.random.default_rng(0)
xyz = (rng.normal(size=(300, 3)) * 2).astype(np.float32)

clicked = reactive.value(None)

ui.page_opts(title="Click a point", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("plot.mode = 'callback': click a point")

        @render_k3d
        def scene():
            plot = k3d.plot(mode="callback")
            plot += k3d.points(
                xyz,
                point_size=0.15,
                color=0x4C78A8,
                click_callback=lambda info: clicked.set(info),
            )
            plot += k3d.points(xyz[:1], point_size=0.3, color=0xE45756, visible=False)
            return plot

        @reactive.effect
        def _highlight():
            info = clicked()
            if info is None:
                return
            highlight = scene.widget.objects[1]
            highlight.positions = np.array([info["position"]], dtype=np.float32)
            highlight.visible = True

    with ui.card():
        ui.card_header("k3d's own click_callback, not an accessor")

        @render.code
        def out():
            info = clicked()
            if info is None:
                return "None (click a point)"
            position = [round(v, 2) for v in info["position"]]
            return f"index: {info['index']}\nposition: {position}"
