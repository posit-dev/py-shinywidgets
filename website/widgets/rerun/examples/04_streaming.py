from __future__ import annotations

import os

if "RERUN_NOTEBOOK_ASSET" not in os.environ:
    os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"

import numpy as np
import rerun as rr
from rerun.notebook import Viewer
from shiny import reactive
from shiny.express import ui

from shinywidgets import render_rerun


def make_path() -> np.ndarray:
    t = np.linspace(0, 4 * np.pi, 200)
    r = 1.5 + 0.08 * t
    return np.column_stack([r * np.cos(t), r * np.sin(t), np.zeros_like(t)])


PATH = make_path()

ui.page_opts(title="Streaming", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("The robot keeps moving after the viewer is already open")

    # Holds the session's RecordingStream so the periodic effect below can log
    # to the same recording the viewer is attached to (the render function
    # itself runs once; new data streams in without a re-render).
    recording_box: list[rr.RecordingStream] = []

    @render_rerun
    def viewer():
        rec = rr.RecordingStream(application_id="streaming")
        recording_box[:] = [rec]
        rec.log("world/path", rr.LineStrips3D([PATH]), static=True)
        return Viewer(width="auto", height="auto", recording=rec)

    # A plain Python counter, not a reactive.Value: an effect that both reads
    # and writes the same reactive.Value re-invalidates itself every tick,
    # which can stall the session badly enough that no output ever flushes
    # (see "Gotchas and limitations"). This effect depends on nothing
    # reactive besides the timer, so a closure variable is simpler anyway.
    step = [0]

    @reactive.effect
    def _stream() -> None:
        reactive.invalidate_later(0.1)
        if not recording_box:
            return
        rec = recording_box[0]
        i = step[0] % len(PATH)
        rec.set_time("step", sequence=step[0])
        rec.log("world/robot", rr.Points3D([PATH[i]], radii=0.3, colors=[(239, 71, 111)]))
        rec.log("robot/battery", rr.Scalars(100 - (step[0] % 200) * 0.5))
        step[0] += 1
