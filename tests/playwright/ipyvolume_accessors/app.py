from __future__ import annotations

import ipyvolume as ipv
import numpy as np
from shiny import App, render, ui
from shinywidgets import output_widget, render_ipyvolume

app_ui = ui.page_fluid(
    output_widget("plot", height="400px"),
    ui.output_text("camera"),
)


def server(input, output, session):
    @render_ipyvolume
    def plot():
        rng = np.random.default_rng(0)
        x, y, z = rng.random((3, 500))
        ipv.figure()
        ipv.scatter(x, y, z, size=1, marker="sphere", color="red")
        return ipv.gcf()

    @render.text
    def camera():
        cam = plot.camera()
        return ",".join(f"{v:.3f}" for v in cam.position)


app = App(app_ui, server)
