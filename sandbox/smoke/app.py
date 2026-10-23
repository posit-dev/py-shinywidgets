import numpy as np
import ipyvolume as ipv
from shiny import App, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.tags.h4("ipyvolume smoke test"),
    output_widget("fig", height="600px"),
)


def server(input, output, session):
    @render_widget
    def fig():
        rng = np.random.default_rng(0)
        x, y, z = rng.random((3, 1000))
        ipv.quickscatter(x, y, z, size=1, marker="sphere")
        return ipv.gcf()


app = App(app_ui, server)
