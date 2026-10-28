from __future__ import annotations

import os

# Serve the viewer's JS/Wasm from the Shiny process (a localhost thread server)
# rather than fetching ~55MB from rerun's CDN. Must be set before importing rerun.
os.environ.setdefault("RERUN_NOTEBOOK_ASSET", "serve-local")

import numpy as np
import rerun as rr
from rerun.notebook import Viewer
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_rerun

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("viewer"),
    ui.output_text("viewer_event"),
)


def server(input, output, session):
    counter = reactive.value(0)
    event = reactive.value("(no events)")

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_rerun
    def viewer():
        counter.get()  # re-render on button click
        rec = rr.RecordingStream(application_id="render_rerun_test")
        rng = np.random.default_rng(counter.get())
        rec.log("points", rr.Points3D(rng.normal(size=(50, 3)), radii=0.05))
        v = Viewer(width="auto", height="auto", recording=rec)
        v.on_event(lambda evt: event.set(type(evt).__name__))
        return v

    @render.text
    def viewer_event():
        return event.get()


app = App(app_ui, server)
