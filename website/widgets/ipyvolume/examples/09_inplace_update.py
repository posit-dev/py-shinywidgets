import ipyvolume as ipv
import numpy as np
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_ipyvolume

# Re-rendering would reset the camera (and re-send all 2,000 points). Mutating
# the already-rendered Scatter's traits in an @reactive.effect instead keeps
# the same WebGL scene -- only the changed trait crosses the wire.
ui.page_opts(title="In-place updates", fillable=True)

ui.input_slider("size", "Point size", 0.2, 3, 1, step=0.1)
ui.input_select("color", "Color", ["tomato", "steelblue", "seagreen"])

rng = np.random.default_rng(0)
pts = rng.normal(size=(3, 2000))


@render_ipyvolume
def plot():
    fig = ipv.figure()
    ipv.scatter(*pts, size=1, marker="sphere", color="tomato")
    return fig


@reactive.effect
def _update_size():
    plot.widget.scatters[0].size = input.size()


@reactive.effect
def _update_color():
    # A single CSS color name is a solid color for every point (cheap, and
    # safe -- see the Gotchas section on *per-point* color arrays).
    plot.widget.scatters[0].color = input.color()


@render.code
def camera_unchanged():
    # Orbit the view, then move the sliders: the camera position you set by
    # dragging is untouched by either effect above.
    cam = plot.camera()
    return f"camera position = ({cam.position[0]:.2f}, {cam.position[1]:.2f}, {cam.position[2]:.2f})"
