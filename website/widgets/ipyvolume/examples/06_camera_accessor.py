import ipyvolume as ipv
import numpy as np
from shiny.express import render, ui

from shinywidgets import render_ipyvolume

ui.page_opts(title="camera() accessor", fillable=True)

ui.markdown("Drag to orbit the scatter; the camera's live position updates below.")


@render_ipyvolume
def plot():
    rng = np.random.default_rng(0)
    x, y, z = rng.normal(size=(3, 300))
    fig = ipv.figure()
    ipv.scatter(x, y, z, size=1, marker="sphere", color="tomato")
    return fig


@render.code
def camera_position():
    # Fires once per completed orbit; the same live pythreejs.Camera instance
    # is returned every time, so read what you need rather than storing it.
    cam = plot.camera()
    return f"position = ({cam.position[0]:.2f}, {cam.position[1]:.2f}, {cam.position[2]:.2f})"
