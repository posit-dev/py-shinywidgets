from __future__ import annotations

import k3d
import numpy as np
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_k3d

N_STEPS = 60
t = np.linspace(0, 2 * np.pi, N_STEPS, endpoint=False)


def orbit(radius: float, speed: float) -> dict[float, np.ndarray]:
    xs, ys = radius * np.cos(speed * t), radius * np.sin(speed * t)
    pos = np.stack([xs, ys, np.zeros_like(xs)], axis=1).astype(np.float32)
    return {float(i) / N_STEPS: pos[i : i + 1] for i in range(N_STEPS)}


ui.page_opts(title="Orbits, driven by a time-keyed trait", fillable=True)
ui.input_action_button("play", "Play")
ui.input_action_button("pause", "Pause")


@render_k3d
def orbits():
    scene = k3d.plot(camera_auto_fit=False, grid_visible=False)
    scene.camera = [0, 0, 14, 0, 0, 0, 0, 1, 0]
    scene += k3d.points([[0, 0, 0]], point_size=0.8, color=0xFFC300, shader="3d")
    scene += k3d.points(orbit(3, 1), point_size=0.4, color=0x1F77B4, shader="3d")
    scene += k3d.points(orbit(5, 0.5), point_size=0.5, color=0xE45756, shader="3d")
    return scene


# start_auto_play()/stop_auto_play() now reach the browser even when called
# directly in the render function (the comm-not-open-yet case no longer drops
# the message) -- but a call made before the k3d view has connected in the
# browser is dropped silently by k3d's JS, and the render function is always
# that early. Calls from later effects work; buttons are the robust version
# of "later", so wire them to buttons.
@reactive.effect
@reactive.event(input.play)
def _play():
    orbits.widget.start_auto_play()


@reactive.effect
@reactive.event(input.pause)
def _pause():
    orbits.widget.stop_auto_play()


@render.text
def time():
    return f"plot.time = {orbits.read('time'):.2f}"
