# Read on demand: nothing in this app reads `viewer.selected()` until the
# button's gated reader runs. Click an entity in the 3D view or the stream
# tree FIRST, then click "Show current selection": the selection you already
# made is there, because the accessor attached and started recording the
# moment the viewer rendered, not on its first read.
from __future__ import annotations

import os

if "RERUN_NOTEBOOK_ASSET" not in os.environ:
    os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"

import rerun as rr
from rerun.notebook import Viewer
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_rerun

ui.page_opts(title="Read the selection on demand", fillable=True)

with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):

        @render_rerun
        def viewer():
            rec = rr.RecordingStream(application_id="read_on_demand_demo")
            rec.log(
                "world/obstacles",
                rr.Boxes3D(
                    centers=[[2.4, 1.2, 0.3], [-1.6, -2.6, 0.3]],
                    half_sizes=[(0.4, 0.4, 0.6)] * 2,
                    colors=[(17, 138, 178)],
                ),
                static=True,
            )
            rec.log(
                "world/robot",
                rr.Points3D([[0, 0, 0]], radii=0.3, colors=[(239, 71, 111)]),
            )
            return Viewer(width="auto", height="auto", recording=rec)

    with ui.card():
        ui.card_header("Click an entity, THEN the button")
        ui.input_action_button("show", "Show current selection")

        @render.code
        @reactive.event(input.show)
        def selection_out():
            evt = viewer.selected()
            if evt is None or not evt.items:
                return "(nothing selected -- click an entity first)"
            return "\n".join(
                f"{type(item).__name__}: {getattr(item, 'entity_path', item)}"
                for item in evt.items
            )
