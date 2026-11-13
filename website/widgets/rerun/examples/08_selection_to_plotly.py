from __future__ import annotations

import os

if "RERUN_NOTEBOOK_ASSET" not in os.environ:
    os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"

import numpy as np
import plotly.graph_objects as go
import rerun as rr
from rerun.notebook import EntitySelectionItem, Viewer
from shiny import reactive
from shiny.express import ui

from shinywidgets import render_plotly, render_rerun

OBSTACLES = np.array([[2.4, 1.2, 0.3], [-1.6, -2.6, 0.3], [3.2, -1.4, 0.3]])
DEFAULT_COLOR = "#118ab2"
SELECTED_COLOR = "#e63946"

ui.page_opts(title="rerun selection highlights a plotly chart", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("3D scene -- click an obstacle")

        @render_rerun
        def viewer():
            rec = rr.RecordingStream(application_id="selection_to_plotly")
            for i, center in enumerate(OBSTACLES):
                # A separate entity path per obstacle, so the selection event
                # names exactly which one was clicked.
                rec.log(
                    f"world/obstacles/{i}",
                    rr.Boxes3D(centers=[center], half_sizes=[(0.4, 0.4, 0.6)], colors=[(17, 138, 178)]),
                    static=True,
                )
            return Viewer(width="auto", height="auto", recording=rec)

    with ui.card(full_screen=True):
        ui.card_header("Top-down view (plotly)")

        @render_plotly
        def scatter():
            fig = go.Figure(
                go.Scatter(
                    x=OBSTACLES[:, 0],
                    y=OBSTACLES[:, 1],
                    mode="markers",
                    marker=dict(size=24, color=[DEFAULT_COLOR] * len(OBSTACLES)),
                )
            )
            fig.update_layout(xaxis_title="x", yaxis_title="y")
            return fig


@reactive.effect
def _highlight_selected_obstacle() -> None:
    evt = viewer.selected()
    if evt is None or not evt.items:
        return
    item = evt.items[0]
    if not isinstance(item, EntitySelectionItem):
        return
    prefix = "world/obstacles/"
    if not item.entity_path.startswith(prefix):
        return
    selected = int(item.entity_path[len(prefix) :])

    with reactive.isolate():
        # In place: the scatter keeps its zoom/pan state, instead of
        # rebuilding the whole figure for a single color change.
        scatter.widget.data[0].marker.color = [
            SELECTED_COLOR if i == selected else DEFAULT_COLOR for i in range(len(OBSTACLES))
        ]
