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


ui.page_opts(title="Update in place", fillable=True)

with ui.layout_columns(col_widths=(9, 3)):
    with ui.card(full_screen=True):
        # `.widget` (what render_rerun exposes) is the low-level viewer; the
        # high-level rerun.notebook.Viewer wrapper's update_panels() and
        # set_time_ctrl() aren't on it. Keep the wrapper itself (and the
        # RecordingStream) to call them later without re-rendering.
        wrapper_box: list[Viewer] = []
        recording_box: list[rr.RecordingStream] = []

        @render_rerun
        def viewer():
            rec = rr.RecordingStream(application_id="update_in_place")
            recording_box[:] = [rec]
            path = make_path()
            rec.log("world/path", rr.LineStrips3D([path]), static=True)
            for i, p in enumerate(path):
                rec.set_time("step", sequence=i)
                rec.log("world/robot", rr.Points3D([p], radii=0.3, colors=[(239, 71, 111)]))
            v = Viewer(width="auto", height="auto", recording=rec)
            wrapper_box[:] = [v]
            return v

    with ui.card():
        ui.card_header("Controls")
        ui.input_action_button("log_more", "Log a new detection", class_="mb-2 w-100")
        ui.input_action_button("toggle_panel", "Toggle blueprint panel", class_="mb-2 w-100")
        ui.input_action_button("replay", "Rewind and play", class_="w-100")

extra_logged = [0]


@reactive.effect
@reactive.event(input.log_more)
def _log_more() -> None:
    # Appends to the live recording -- no re-render, so the viewer's camera
    # angle and selection are untouched.
    if not recording_box:
        return
    extra_logged[0] += 1
    rec = recording_box[0]
    rec.set_time("step", sequence=N_STEPS + extra_logged[0])
    rng = np.random.default_rng(extra_logged[0])
    point = rng.uniform(-4, 4, size=3) * [1, 1, 0]
    rec.log("world/detections", rr.Points3D([point], radii=0.25, colors=[(6, 214, 160)]))


panel_state = ["expanded"]


@reactive.effect
@reactive.event(input.toggle_panel)
def _toggle_panel() -> None:
    if not wrapper_box:
        return
    panel_state[0] = "collapsed" if panel_state[0] == "expanded" else "expanded"
    wrapper_box[0].update_panels(blueprint=panel_state[0])


@reactive.effect
@reactive.event(input.replay)
def _replay() -> None:
    if wrapper_box:
        wrapper_box[0].set_time_ctrl(sequence=0, play=True)
