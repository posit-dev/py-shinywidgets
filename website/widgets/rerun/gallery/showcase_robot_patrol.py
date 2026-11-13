# Robot patrol dashboard -- showcase, ~150 lines
# A live-streaming robot patrol: a custom dark blueprint (3D scene + telemetry
# + event log), a pause/scrub control pair (Shiny drives the viewer's time
# control while the stream is paused), a "log an event" button (Shiny input ->
# what gets logged), and a selection-driven detail panel (viewer -> Shiny).
# Run: shiny run docs/widget-guides/rerun/gallery/showcase_robot_patrol.py
# Data: a synthetic patrol route and obstacles (no external data needed).

from __future__ import annotations

import os

if "RERUN_NOTEBOOK_ASSET" not in os.environ:
    os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"

from typing import Dict, List, Tuple

import numpy as np
import rerun as rr
import rerun.blueprint as rrb
from rerun.notebook import EntitySelectionItem, Viewer
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_rerun

OBSTACLES = np.array([[2.4, 1.2, 0.3], [-1.6, -2.6, 0.3], [3.2, -1.4, 0.3]])

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

ui.page_opts(title="Robot patrol dashboard", fillable=True)

# Entity path -> logged (step, x, y) rows, for the selection detail panel --
# the viewer's selection event only names the entity, not its history.
HISTORY: Dict[str, List[Tuple[int, float, float]]] = {"world/robot": []}

with ui.layout_columns(col_widths=(9, 3)):
    with ui.card(full_screen=True):
        wrapper_box: list[Viewer] = []
        recording_box: list[rr.RecordingStream] = []

        @render_rerun
        def viewer():
            rec = rr.RecordingStream(application_id="robot_patrol")
            recording_box[:] = [rec]
            rec.log(
                "world/obstacles",
                rr.Boxes3D(centers=OBSTACLES, half_sizes=[(0.4, 0.4, 0.6)] * 3, colors=[(17, 138, 178)]),
                static=True,
            )
            v = Viewer(width="auto", height="auto", blueprint=BLUEPRINT, theme="dark", recording=rec)
            wrapper_box[:] = [v]
            return v

    with ui.card():
        ui.card_header("Controls")
        ui.input_switch("paused", "Pause streaming", value=False)
        ui.input_slider("scrub", "Scrub (while paused)", min=0, max=300, value=0)
        ui.input_action_button("log_event", "Log an event", class_="w-100 mt-2")

    with ui.card():
        ui.card_header("Selection detail")

        @render.ui
        def detail():
            evt = viewer.selected()
            if evt is None or not evt.items:
                return ui.p("Click the robot or an obstacle.")
            item = evt.items[0]
            if not isinstance(item, EntitySelectionItem):
                return ui.p(f"Selected a {type(item).__name__}.")
            rows = HISTORY.get(item.entity_path, [])[-5:]
            if not rows:
                return ui.TagList(ui.h6(item.entity_path), ui.p("(static entity, no history tracked)"))
            return ui.TagList(
                ui.h6(item.entity_path),
                ui.tags.ul(*[ui.tags.li(f"#{i}: ({x:.2f}, {y:.2f})") for i, x, y in rows]),
            )


step = [0]


@reactive.effect
def _stream() -> None:
    reactive.invalidate_later(0.1)
    if not recording_box or input.paused():
        return
    rec = recording_box[0]
    i = step[0]
    angle = i / 15
    r = 1.5 + 0.02 * (i % 150)
    x, y = r * np.cos(angle), r * np.sin(angle)
    rec.set_time("step", sequence=i)
    rec.log("world/robot", rr.Points3D([(x, y, 0)], radii=0.3, colors=[(239, 71, 111)]))
    rec.log("robot/speed", rr.Scalars(1.0 + 0.3 * np.sin(i / 20)))
    rec.log("robot/battery", rr.Scalars(max(0, 100 - (i % 600) * 0.15)))
    HISTORY["world/robot"].append((i, x, y))
    step[0] += 1


@reactive.effect
def _scrub_when_paused() -> None:
    if wrapper_box and input.paused():
        wrapper_box[0].set_time_ctrl(sequence=input.scrub())


@reactive.effect
@reactive.event(input.log_event)
def _log_event() -> None:
    if not recording_box:
        return
    rec = recording_box[0]
    rec.set_time("step", sequence=step[0])
    rec.log("robot/log", rr.TextLog(f"operator event at step {step[0]}", level="INFO"))
