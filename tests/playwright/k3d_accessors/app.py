from __future__ import annotations

import k3d
import numpy as np
from shiny import App, render, ui
from shinywidgets import output_widget, render_k3d

app_ui = ui.page_fluid(
    output_widget("plot", height="400px"),
    ui.output_text("camera"),
)


def server(input, output, session):
    @render_k3d
    def plot():
        rng = np.random.default_rng(0)
        positions = rng.random((200, 3), dtype=np.float32)
        p = k3d.plot()
        p += k3d.points(positions, point_size=0.05, color=0xFF0000)
        return p

    @render.text
    def camera():
        return ",".join(f"{v:.3f}" for v in plot.camera())


app = App(app_ui, server)
