import ipyvolume as ipv
import numpy as np
from shiny.express import ui

from shinywidgets import render_ipyvolume, render_widget

ui.page_opts(title="Animation", fillable=True)

# A helix traced out over time: shape (frames, points, 3). The first axis is
# the animation sequence -- get this axis order wrong and the animation plays
# the wrong dimension.
t = np.linspace(0, 4 * np.pi, 300)
helix = np.stack([np.cos(t), np.sin(t), t / 4], axis=1)
frames = np.stack([np.roll(helix, -i, axis=0)[:40] for i in range(len(t))])


@render_ipyvolume
def plot():
    fig = ipv.figure()
    ipv.scatter(
        frames[:, :, 0], frames[:, :, 1], frames[:, :, 2], size=1.5, marker="sphere", color="steelblue"
    )
    return fig


@render_widget
def controls():
    fig = plot.value  # re-runs once `plot` first renders (None before that)
    if fig is None:
        return None
    # add=False returns the Play/slider HBox; the default add=True instead
    # targets the pylab container (invisible here, since `plot` returns the
    # bare Figure) and returns None.
    return ipv.animation_control(fig.scatters[0], add=False, interval=40)
