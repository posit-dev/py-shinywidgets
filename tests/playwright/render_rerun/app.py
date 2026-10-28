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

# Identifiable payloads so the tests can verify logged data actually reaches
# the browser (they show up, base64-encoded, in the websocket comm messages)
PRE_RENDER_MARKER = "PRE_RENDER_MARKER_7f3a2c"
POST_RENDER_MARKER = "POST_RENDER_MARKER_9d1e4b"

app_ui = ui.page_fillable(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_action_button("log_more", "Log more data"),
    ui.output_text("render_count"),
    ui.card(
        ui.card_header("Viewer"),
        output_widget("viewer"),
        height="500px",
    ),
    # An output with an explicit height isn't fillable, so the viewer gets no
    # forward-fill-potential styling; shinywidgets.css must fit it to the
    # output instead (otherwise its 16:9 default sizing overflows and clips)
    ui.card(
        ui.card_header("Viewer (explicit output height)"),
        output_widget("viewer_fixed", height="250px"),
    ),
    # A non-fillable output with no height sizes to the viewer's content (its
    # default 16:9 sizing)
    ui.card(
        ui.card_header("Viewer (non-filling output)"),
        output_widget("viewer_plain", fill=False, fillable=False),
    ),
    ui.output_text("viewer_event"),
)


def server(input, output, session):
    counter = reactive.value(0)
    event = reactive.value("(no events)")
    recordings = []

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
        recordings[:] = [rec]
        rng = np.random.default_rng(counter.get())
        rec.log("points", rr.Points3D(rng.normal(size=(50, 3)), radii=0.05))
        # Logged before the viewer (and its callback sink) exists; rerun
        # replays it to the widget when Viewer() attaches the sink
        rec.log("logs", rr.TextLog(PRE_RENDER_MARKER))
        # Leave width/height at their 640x480 defaults to exercise the
        # "defaults mean fill the container" conversion
        v = Viewer(recording=rec)
        v.on_event(lambda evt: event.set(type(evt).__name__))
        return v

    def _plain_viewer(seed: int):
        rec = rr.RecordingStream(application_id="render_rerun_sizing_test")
        rng = np.random.default_rng(seed)
        rec.log("points", rr.Points3D(rng.normal(size=(50, 3)), radii=0.05))
        # Leave width/height at their 640x480 defaults (as with `viewer`)
        return Viewer(recording=rec)

    @render_rerun
    def viewer_fixed():
        return _plain_viewer(1)

    @render_rerun
    def viewer_plain():
        return _plain_viewer(2)

    @reactive.effect
    @reactive.event(input.log_more)
    def _():
        if recordings:
            # Log to the currently mounted viewer's recording after render
            recordings[0].log("logs", rr.TextLog(POST_RENDER_MARKER))
            recordings[0].flush()

    @render.text
    def viewer_event():
        return event.get()


app = App(app_ui, server)
