from __future__ import annotations

import pythreejs as p3
from shiny import App, render, ui
from shinywidgets import output_widget, render_pythreejs

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Re-render"),
    ui.output_text("render_count"),
    output_widget("plot"),
)


def server(input, output, session):
    @render_pythreejs
    def plot():
        input.rerender()
        box = p3.Mesh(
            p3.BoxGeometry(1, 1, 1),
            p3.MeshStandardMaterial(color="red"),
        )
        # Default target/shadow: the browser creates those models (plus the
        # shadow's camera), so a re-render used to leak ~3 models per light
        light = p3.DirectionalLight(color="white", intensity=1.0)
        light.position = (3, 5, 2)
        ambient = p3.AmbientLight(color="white", intensity=0.4)
        camera = p3.PerspectiveCamera(position=(3, 3, 3))
        scene = p3.Scene(children=[box, light, ambient])
        controls = p3.OrbitControls(controlling=camera)
        return p3.Renderer(
            camera=camera, scene=scene, controls=[controls], width=400, height=300
        )

    @render.text
    def render_count():
        return str(input.rerender())


app = App(app_ui, server)
