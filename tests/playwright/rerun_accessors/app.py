from __future__ import annotations

import os

# Serve the viewer's JS/Wasm from the Shiny process (a localhost thread server)
# rather than fetching ~55MB from rerun's CDN. Must be set before importing rerun.
os.environ.setdefault("RERUN_NOTEBOOK_ASSET", "serve-local")

import rerun as rr
from rerun.notebook import Viewer
from shiny import App, render, ui
from shinywidgets import output_widget, render_rerun

app_ui = ui.page_fillable(
    ui.card(
        ui.card_header("Viewer"),
        output_widget("viewer"),
        height="500px",
    ),
    ui.output_text_verbatim("selection"),
)


def server(input, output, session):
    @render_rerun
    def viewer():
        rec = rr.RecordingStream(application_id="test_rerun_accessors")
        rec.log("points", rr.Points3D([[0, 0, 0], [1, 1, 1], [2, 0, 2]]))
        return Viewer(recording=rec)

    @render.text
    def selection():
        evt = viewer.selection()
        if evt is None:
            return "(waiting)"
        return "[" + ", ".join(type(item).__name__ for item in evt.items) + "]"


app = App(app_ui, server)
