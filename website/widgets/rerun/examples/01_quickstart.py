from __future__ import annotations

import os

# Serve the viewer's JS/Wasm bundle from the Shiny process instead of rerun's
# CDN (see "Installation" in the guide for why). Shiny Express auto-displays
# any top-level expression's value, so this is an `if`, not `.setdefault()`
# (whose return value would otherwise render as page text).
if "RERUN_NOTEBOOK_ASSET" not in os.environ:
    os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"

import numpy as np
import rerun as rr
from rerun.notebook import Viewer
from shiny.express import ui

from shinywidgets import render_rerun

ui.page_opts(title="rerun quickstart", fillable=True)

with ui.card(full_screen=True):

    @render_rerun
    def viewer():
        # Create the recording inside the render function so each session
        # gets its own -- never the global rr.init()/rr.log() pattern, which
        # would mix every session's data into one recording.
        rec = rr.RecordingStream(application_id="quickstart")

        rng = np.random.default_rng(0)
        t = np.linspace(0, 4 * np.pi, 120)
        path = np.column_stack([np.cos(t) * t, np.sin(t) * t, t * 0.1])
        rec.log("world/path", rr.LineStrips3D([path]), static=True)

        for i in range(0, len(path), 4):
            rec.set_time("step", sequence=i)
            rec.log("world/robot", rr.Points3D([path[i]], radii=0.3, colors=[(239, 71, 111)]))
            rec.log("robot/speed", rr.Scalars(1.0 + 0.4 * np.sin(i / 8) + rng.normal(0, 0.05)))

        return Viewer(width="auto", height="auto", recording=rec)
