from __future__ import annotations

import os

if "RERUN_NOTEBOOK_ASSET" not in os.environ:
    os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"

import numpy as np
import rerun as rr
from rerun.notebook import Viewer
from shiny import reactive
from shiny.express import input, ui

from shinywidgets import render_rerun

N_STEPS = 40


def make_path() -> np.ndarray:
    t = np.linspace(0, 4 * np.pi, N_STEPS)
    r = 1.5 + 0.12 * t
    return np.column_stack([r * np.cos(t), r * np.sin(t), np.zeros(N_STEPS)])


ui.page_opts(title="A Shiny slider scrubs the timeline", fillable=True)
ui.input_slider("step", "Step", min=0, max=N_STEPS - 1, value=0)

with ui.card(full_screen=True):
    wrapper_box: list[Viewer] = []

    @render_rerun
    def viewer():
        rec = rr.RecordingStream(application_id="slider_scrub")
        path = make_path()
        rec.log("world/path", rr.LineStrips3D([path]), static=True)
        for i, p in enumerate(path):
            rec.set_time("step", sequence=i)
            rec.log("world/robot", rr.Points3D([p], radii=0.3, colors=[(239, 71, 111)]))
            rec.log("robot/speed", rr.Scalars(1.0 + 0.3 * np.sin(i / 5)))
        v = Viewer(width="auto", height="auto", recording=rec)
        wrapper_box[:] = [v]
        return v


@reactive.effect
def _scrub() -> None:
    # A Shiny slider stands in for the viewer's own timeline scrubber -- handy
    # when the rest of the page (other inputs, a linked table) should drive
    # "what point in time am I looking at" instead of the viewer's own UI.
    if wrapper_box:
        wrapper_box[0].set_time_ctrl(sequence=input.step())
