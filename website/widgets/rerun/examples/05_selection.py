from __future__ import annotations

import os

if "RERUN_NOTEBOOK_ASSET" not in os.environ:
    os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"

from typing import Dict, List, Tuple

import numpy as np
import rerun as rr
from rerun.notebook import EntitySelectionItem, Viewer
from shiny.express import render, ui

from shinywidgets import render_rerun

N_STEPS = 40
OBSTACLES = np.array([[2.4, 1.2, 0.3], [-1.6, -2.6, 0.3]])

# Rerun's selection event only names the entity path, not what was logged
# there -- keep that ourselves, keyed by entity path, so a click can look up
# the values behind it.
HISTORY: Dict[str, List[Tuple[int, float, float, float]]] = {}

ui.page_opts(title="Selection accessor", fillable=True)

with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):

        @render_rerun
        def viewer():
            rec = rr.RecordingStream(application_id="selection_demo")
            t = np.linspace(0, 4 * np.pi, N_STEPS)
            r = 1.5 + 0.12 * t
            path = np.column_stack([r * np.cos(t), r * np.sin(t), np.zeros(N_STEPS)])

            HISTORY["world/robot"] = []
            for i, p in enumerate(path):
                rec.set_time("step", sequence=i)
                rec.log("world/robot", rr.Points3D([p], radii=0.3, colors=[(239, 71, 111)]))
                HISTORY["world/robot"].append((i, *p))

            rec.log(
                "world/obstacles",
                rr.Boxes3D(centers=OBSTACLES, half_sizes=[(0.4, 0.4, 0.6)] * 2, colors=[(17, 138, 178)]),
                static=True,
            )
            HISTORY["world/obstacles"] = [
                (i, *center) for i, center in enumerate(OBSTACLES)
            ]

            return Viewer(width="auto", height="auto", recording=rec)

    with ui.card():
        ui.card_header("Selection detail")

        @render.ui
        def detail():
            evt = viewer.selected()
            if evt is None:
                return ui.p("(nothing selected yet -- click an entity in the 3D view or the stream tree)")
            if not evt.items:
                return ui.p("Nothing selected -- click an entity in the 3D view or the stream tree.")

            item = evt.items[0]
            if not isinstance(item, EntitySelectionItem):
                return ui.p(f"Selected a {type(item).__name__}, not an entity.")

            rows = HISTORY.get(item.entity_path, [])
            return ui.TagList(
                ui.h5(item.entity_path),
                ui.p(f"{len(rows)} logged value(s)"),
                ui.tags.table(
                    ui.tags.thead(ui.tags.tr(ui.tags.th("#"), ui.tags.th("x"), ui.tags.th("y"), ui.tags.th("z"))),
                    ui.tags.tbody(
                        *[
                            ui.tags.tr(
                                ui.tags.td(str(i)),
                                ui.tags.td(f"{x:.2f}"),
                                ui.tags.td(f"{y:.2f}"),
                                ui.tags.td(f"{z:.2f}"),
                            )
                            for i, x, y, z in (rows[:3] + rows[-3:] if len(rows) > 6 else rows)
                        ]
                    ),
                    class_="table table-sm",
                ),
            )
