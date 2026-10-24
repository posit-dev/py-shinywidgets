from __future__ import annotations

import os

import ipyvolume as ipv
import numpy as np
from shiny import App, ui
from shinywidgets import output_widget, render_ipyvolume

N = int(os.environ.get("N", "10000"))

app_ui = ui.page_fluid(output_widget("plot", height="500px"))


def server(input, output, session):
    @render_ipyvolume
    def plot():
        rng = np.random.default_rng(0)
        x, y, z = rng.random((3, N)).astype(np.float32)
        fig = ipv.Figure()
        scatter = ipv.widgets.Scatter(
            x=x, y=y, z=z, size=1, marker="sphere", color="red",
            size_selected=1, color_selected="red",
        )
        fig.scatters = [scatter]
        return fig


app = App(app_ui, server)
