from __future__ import annotations

import os

if "RERUN_NOTEBOOK_ASSET" not in os.environ:
    os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"

import numpy as np
import rerun as rr
import rerun.blueprint as rrb
from rerun.notebook import Viewer
from shiny.express import ui

from shinywidgets import render_rerun

N_STEPS = 60


def make_path() -> np.ndarray:
    t = np.linspace(0, 4 * np.pi, N_STEPS)
    r = 1.5 + 0.12 * t
    return np.column_stack([r * np.cos(t), r * np.sin(t), np.zeros(N_STEPS)])


# A blueprint arranges views by entity path (`origin`) rather than leaving
# rerun to auto-layout everything it sees -- a 3D scene on the left, telemetry
# and the event log stacked on the right, dark theme, and the blueprint/
# selection side panels collapsed for an end-user dashboard rather than a
# debugging tool.
BLUEPRINT = rrb.Blueprint(
    rrb.Horizontal(
        rrb.Spatial3DView(origin="world", name="Scene"),
        rrb.Vertical(
            rrb.TimeSeriesView(origin="robot", name="Telemetry"),
            rrb.TextLogView(origin="robot/log", name="Events"),
        ),
        column_shares=[2, 1],
    ),
    collapse_panels=True,
)

ui.page_opts(title="Blueprint layout", fillable=True)

with ui.card(full_screen=True):

    @render_rerun
    def viewer():
        rec = rr.RecordingStream(application_id="blueprint_layout")
        path = make_path()
        rec.log("world/path", rr.LineStrips3D([path]), static=True)

        for i in range(N_STEPS):
            rec.set_time("step", sequence=i)
            rec.log("world/robot", rr.Points3D([path[i]], radii=0.3, colors=[(239, 71, 111)]))
            rec.log("robot/speed", rr.Scalars(1.0 + 0.3 * np.sin(i / 5)))
            rec.log("robot/battery", rr.Scalars(100 - i * 0.6))
            if i == N_STEPS // 2:
                rec.log("robot/log", rr.TextLog("waypoint reached", level="INFO"))

        return Viewer(width="auto", height="auto", blueprint=BLUEPRINT, theme="dark", recording=rec)
