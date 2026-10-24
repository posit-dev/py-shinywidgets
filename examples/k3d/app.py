from __future__ import annotations

import k3d
import numpy as np
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_k3d

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_slider("n", "Number of points", min=100, max=5000, value=1000),
        ui.input_slider("point_size", "Point size", min=0.01, max=0.2, value=0.05),
        ui.input_action_button("shuffle", "Resample"),
        ui.h6("Camera position"),
        ui.output_text_verbatim("camera"),
    ),
    ui.card(
        ui.card_header("Drag to orbit, scroll to zoom"),
        output_widget("scene"),
        full_screen=True,
    ),
    title="k3d",
    fillable=True,
)


def server(input, output, session):
    @reactive.calc
    def positions():
        input.shuffle()
        rng = np.random.default_rng()
        return rng.normal(size=(input.n(), 3)).astype(np.float32)

    @render_k3d
    def scene():
        xyz = positions()
        plot = k3d.plot()
        plot += k3d.points(xyz, attribute=xyz[:, 2], point_size=0.05)
        return plot

    # Changing the point size updates the existing scene in place (the camera
    # stays wherever the user left it) rather than re-rendering the output
    @reactive.effect
    def _():
        plot = scene.widget
        with reactive.isolate():
            points = plot.objects[0]
        points.point_size = input.point_size()

    @render.text
    def camera():
        position = reactive_read(scene.widget, "camera")[:3]
        return ", ".join(f"{x:.2f}" for x in position)


app = App(app_ui, server)
