import ipyvolume as ipv
import numpy as np
from shiny import reactive
from shiny.express import ui

from shinywidgets import render_ipyvolume

# camera() driving another view: orbit the big plot, and a small "chase" view
# mirrors the same camera pose -- a common pattern for a detail/overview pair.
ui.page_opts(title="Linked camera views", fillable=True)

rng = np.random.default_rng(0)
pts = rng.normal(size=(3, 1500))

with ui.layout_columns(col_widths=(8, 4)):
    with ui.card():
        ui.card_header("Orbit this one")

        @render_ipyvolume
        def main_plot():
            fig = ipv.figure()
            ipv.scatter(*pts, size=0.8, marker="sphere", color="tomato")
            return fig

    with ui.card():
        ui.card_header("Chase view (mirrors the camera)")

        @render_ipyvolume
        def chase_plot():
            fig = ipv.figure()
            ipv.scatter(*pts, size=0.8, marker="sphere", color="steelblue")
            return fig


@reactive.effect
def _sync_chase_camera():
    cam = main_plot.camera()
    chase_cam = chase_plot.widget.camera
    chase_cam.position = cam.position
    chase_cam.quaternion = cam.quaternion
    chase_cam.zoom = cam.zoom
