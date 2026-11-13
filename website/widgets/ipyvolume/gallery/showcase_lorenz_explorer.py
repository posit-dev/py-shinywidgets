# Title: Lorenz attractor explorer
# A more involved demo: a comet animates along a chaotic trajectory colored
# by local speed, with a camera readout, an in-place size/highlight restyle,
# and a companion 2D chart synced to the animation frame via reactive_read.
# Bucket: showcase (~150 lines).
# Run: uv run shiny run gallery/showcase_lorenz_explorer.py
# Data: synthetic (a numerically integrated Lorenz system -- no real dataset
# fits a specific chaotic trajectory; the point is the shape and dynamics).
from __future__ import annotations

import ipyvolume as ipv
import numpy as np
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import reactive_read, render_ipyvolume, render_widget

ui.page_opts(title="Lorenz attractor explorer", fillable=True)


def lorenz(n=12000, dt=0.006, sigma=10.0, rho=28.0, beta=8 / 3):
    pts = np.empty((n, 3))
    p = np.array([1.0, 1.0, 1.0])
    for i in range(n):
        v = np.array([sigma * (p[1] - p[0]), p[0] * (rho - p[2]) - p[1], p[0] * p[1] - beta * p[2]])
        p += dt * v
        pts[i] = p
    speed = np.linalg.norm(np.gradient(pts, axis=0), axis=1)
    return pts, speed


PTS, SPEED = lorenz()
XYZ = (PTS - PTS.mean(axis=0)) / PTS.std(axis=0) / 2.5


def ramp(t: np.ndarray) -> np.ndarray:
    """Purple -> orange -> yellow ramp, t in [0, 1], returns an (N, 3) float array."""
    stops = np.array([[0.27, 0.0, 0.35], [0.78, 0.18, 0.42], [0.99, 0.65, 0.18], [1.0, 0.95, 0.55]])
    idx = np.clip(t * (len(stops) - 1), 0, len(stops) - 1.001).astype(int)
    frac = (t * (len(stops) - 1)) % 1.0
    return stops[idx] * (1 - frac[:, None]) + stops[idx + 1] * frac[:, None]


BASE_COLOR = ramp((SPEED - SPEED.min()) / (np.ptp(SPEED) + 1e-9)).astype(np.float32)
FASTEST = np.argsort(SPEED)[-int(0.01 * len(SPEED)) :]  # fastest 1% of the trajectory

# Comet: (S frames, TAIL points, 3) -- the first axis is the animation sequence
S, TAIL = 150, 70
starts = np.linspace(0, len(XYZ) - TAIL - 1, S).astype(int)
COMET = np.stack([XYZ[s : s + TAIL] for s in starts], axis=0).astype(np.float32)

with ui.sidebar(width=280):
    ui.input_slider("size", "Point size", 0.1, 1.5, 0.4, step=0.05)
    ui.input_checkbox("fast", "Highlight the fastest 1%", False)
    ui.markdown(
        "Drag to orbit, scroll to zoom. Press Play below the plot to animate "
        "a comet along the trajectory."
    )
    ui.hr()

    @render.code
    def state():
        cam = plot.camera()
        frame = reactive_read(plot.widget.scatters[1], "sequence_index") if plot.widget else 0
        return (
            f"camera = ({cam.position[0]:.2f}, {cam.position[1]:.2f}, {cam.position[2]:.2f})\n"
            f"frame  = {frame}"
        )


with ui.card(full_screen=True):
    ui.card_header("12,000 points, colored by local speed")

    @render_ipyvolume
    def plot():
        fig = ipv.figure()
        cloud = ipv.widgets.Scatter(
            x=XYZ[:, 0], y=XYZ[:, 1], z=XYZ[:, 2],
            color=BASE_COLOR, size=0.35, marker="sphere",
            size_selected=0.35, color_selected="gold",  # required: 0-d defaults don't serialize
        )
        comet = ipv.widgets.Scatter(
            x=COMET[:, :, 0], y=COMET[:, :, 1], z=COMET[:, :, 2],
            color="gold", size=0.6, marker="sphere",
            size_selected=0.6, color_selected="gold",
        )
        fig.scatters = [cloud, comet]
        # Direct construction doesn't auto-fit axes (default box is [0, 1]^3)
        fig.xlim = [float(XYZ[:, 0].min()), float(XYZ[:, 0].max())]
        fig.ylim = [float(XYZ[:, 1].min()), float(XYZ[:, 1].max())]
        fig.zlim = [float(XYZ[:, 2].min()), float(XYZ[:, 2].max())]
        fig.style = ipv.styles.dark
        fig.camera.position = (0.9, -1.2, 0.8)
        return fig

    @render_widget
    def controls():
        fig = plot.value  # re-runs once `plot` first renders (None before that)
        if fig is None:
            return None
        # add=False returns the Play/slider widget; the default add=True
        # instead targets the pylab container (unused here) and returns None.
        return ipv.animation_control(fig.scatters[1], add=False, interval=45)


# In-place updates: restyle the point cloud without re-sending any data or
# resetting the camera/animation.
@reactive.effect
def _resize():
    plot.widget.scatters[0].size = input.size()


@reactive.effect
def _highlight_fast():
    color = BASE_COLOR.copy()
    if input.fast():
        color[FASTEST] = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    plot.widget.scatters[0].color = color
