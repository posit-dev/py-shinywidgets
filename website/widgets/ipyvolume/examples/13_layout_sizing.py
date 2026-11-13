import ipyvolume as ipv
import numpy as np
from shiny.express import ui

from shinywidgets import render_ipyvolume

ui.page_opts(title="Layout and sizing", fillable=True)

rng = np.random.default_rng(0)
pts = rng.normal(size=(3, 500))


def make_fig(**kwargs):
    fig = ipv.figure(**kwargs)
    ipv.scatter(*pts, size=1, marker="sphere", color="tomato")
    return fig


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Fills its card (try full_screen)")

        @render_ipyvolume
        def fill_plot():
            return make_fig()

    with ui.card():
        ui.card_header("Explicit figure size (400x300px): clipped, not stretched")

        @render_ipyvolume
        def fixed_plot():
            return make_fig(width=400, height=300)
