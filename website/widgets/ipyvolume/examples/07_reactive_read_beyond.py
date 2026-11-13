import ipyvolume as ipv
import numpy as np
from shiny.express import render, ui

from shinywidgets import reactive_read, render_ipyvolume, render_widget

ui.page_opts(title="Beyond the accessors", fillable=True)

t = np.linspace(0, 4 * np.pi, 300)
helix = np.stack([np.cos(t), np.sin(t), t / 4], axis=1)
frames = np.stack([np.roll(helix, -i, axis=0)[:40] for i in range(len(t))])

with ui.card(height="320px"):

    @render_ipyvolume
    def plot():
        fig = ipv.figure()
        ipv.scatter(
            frames[:, :, 0], frames[:, :, 1], frames[:, :, 2], size=1.5, marker="sphere", color="steelblue"
        )
        return fig


@render_widget
def controls():
    fig = plot.value
    if fig is None:
        return None
    return ipv.animation_control(fig.scatters[0], add=False, interval=40)


@render.code
def state():
    # The browser syncs the figure's resized canvas back to these traits, and
    # the Play control advances this trait as it animates -- neither is an
    # accessor (no dedicated method), but both are ordinary synced traits.
    w = reactive_read(plot.widget, "width")
    h = reactive_read(plot.widget, "height")
    frame = reactive_read(plot.widget.scatters[0], "sequence_index")
    return f"canvas = {w}x{h}px\nframe = {frame}"
