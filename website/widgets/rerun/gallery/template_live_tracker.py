# Live tracker -- template, ~70 lines
# A point that moves every tick, logged to a recording that's already attached
# to an open viewer (no re-render), plus a selection-driven detail panel.
# Adapt by swapping what gets logged each tick (a real sensor feed, a queue
# drained from a background thread, ...) and what HISTORY tracks.
# Run: shiny run docs/widget-guides/rerun/gallery/template_live_tracker.py
# Data: a synthetic circular walk (no external data needed).

from __future__ import annotations

import os

if "RERUN_NOTEBOOK_ASSET" not in os.environ:
    os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"

from typing import Dict, List, Tuple

import numpy as np
import rerun as rr
from rerun.notebook import EntitySelectionItem, Viewer
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import render_rerun

ui.page_opts(title="Live tracker", fillable=True)

HISTORY: Dict[str, List[Tuple[int, float, float]]] = {"world/tracker": []}

with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):
        recording_box: list[rr.RecordingStream] = []

        @render_rerun
        def viewer():
            rec = rr.RecordingStream(application_id="live_tracker")
            recording_box[:] = [rec]
            return Viewer(width="auto", height="auto", recording=rec)

    with ui.card():
        ui.card_header("Selected entity")

        @render.ui
        def detail():
            evt = viewer.selected()
            if evt is None or not evt.items:
                return ui.p("Click the tracked point to see its recent path.")
            item = evt.items[0]
            if not isinstance(item, EntitySelectionItem):
                return ui.p(f"Selected a {type(item).__name__}.")
            rows = HISTORY.get(item.entity_path, [])[-5:]
            return ui.TagList(
                ui.h6(item.entity_path),
                ui.tags.ul(*[ui.tags.li(f"#{i}: ({x:.2f}, {y:.2f})") for i, x, y in rows]),
            )


tick = [0]


@reactive.effect
def _tick() -> None:
    reactive.invalidate_later(0.2)
    if not recording_box:
        return
    rec = recording_box[0]
    i = tick[0]
    angle = i / 10
    x, y = np.cos(angle) * 2, np.sin(angle) * 2
    rec.set_time("tick", sequence=i)
    rec.log("world/tracker", rr.Points3D([(x, y, 0)], radii=0.25, colors=[(239, 71, 111)]))
    HISTORY["world/tracker"].append((i, x, y))
    tick[0] += 1
