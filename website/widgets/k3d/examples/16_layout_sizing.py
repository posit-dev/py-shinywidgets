from __future__ import annotations

import k3d
import numpy as np
from ipywidgets import Layout
from shiny.express import ui
from shinywidgets import render_k3d

rng = np.random.default_rng(0)
xyz = (rng.random((200, 3), dtype=np.float32))


def make_plot(**kwargs) -> k3d.Plot:
    plot = k3d.plot(**kwargs)
    plot += k3d.points(xyz, point_size=0.05, color=0x4C78A8)
    return plot


ui.page_opts(title="Sizing", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        "Fills its card (no explicit height) -- try full_screen"

        @render_k3d
        def fills():
            return make_plot()

    with ui.card():
        "Fixed height via k3d.plot(height=250)"

        @render_k3d
        def fixed_height():
            return make_plot(height=250)

    with ui.card():
        "Fixed height via ipywidgets Layout(height='250px')"

        @render_k3d
        def layout_height():
            plot = make_plot()
            plot.layout = Layout(height="250px")
            return plot
