import ipyvolume as ipv
import numpy as np
from shiny.express import render, ui

from shinywidgets import reactive_read, render_ipyvolume, render_widget

# Animated scatter driving a 2D companion chart: `sequence_index` isn't an
# accessor (ipyvolume has none for it), but it's an ordinary synced trait, so
# `reactive_read()` turns the Play button's current frame into a reactive
# value any other output can use -- here, a vertical marker on a speed chart.
ui.page_opts(title="Sequence index -> companion chart", fillable=True)


def lorenz(n=4000, dt=0.006, sigma=10.0, rho=28.0, beta=8 / 3):
    pts = np.empty((n, 3))
    p = np.array([1.0, 1.0, 1.0])
    for i in range(n):
        v = np.array([sigma * (p[1] - p[0]), p[0] * (rho - p[2]) - p[1], p[0] * p[1] - beta * p[2]])
        p += dt * v
        pts[i] = p
    speed = np.linalg.norm(np.gradient(pts, axis=0), axis=1)
    return pts, speed


pts, speed = lorenz()
xyz = (pts - pts.mean(axis=0)) / pts.std(axis=0)

S, TAIL = 120, 50
starts = np.linspace(0, len(xyz) - TAIL - 1, S).astype(int)
comet = np.stack([xyz[s : s + TAIL] for s in starts], axis=0).astype(np.float32)

with ui.layout_columns():
    with ui.card():
        ui.card_header("Comet along the Lorenz attractor")

        @render_ipyvolume
        def plot():
            fig = ipv.figure()
            ipv.scatter(comet[:, :, 0], comet[:, :, 1], comet[:, :, 2], size=1, marker="sphere", color="tomato")
            return fig

        @render_widget
        def controls():
            fig = plot.value
            if fig is None:
                return None
            return ipv.animation_control(fig.scatters[0], add=False, interval=50)

    with ui.card():
        ui.card_header("Speed along the trajectory (marker = current frame)")

        @render.plot
        def speed_chart():
            import matplotlib.pyplot as plt

            frame = reactive_read(plot.widget.scatters[0], "sequence_index")
            fig, ax = plt.subplots()
            ax.plot(speed, color="steelblue", linewidth=0.8)
            ax.axvline(starts[frame], color="tomato", linewidth=2)
            ax.set_xlabel("step")
            ax.set_ylabel("speed")
            return fig
