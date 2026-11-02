from __future__ import annotations

import pythreejs as p3
from shiny import App, render, ui
from shinywidgets import output_widget, render_pythreejs

app_ui = ui.page_fluid(
    output_widget("scene", height="400px"),
    ui.output_text("camera"),
)


def server(input, output, session):
    @render_pythreejs
    def scene():
        sc = p3.Scene()
        camera = p3.PerspectiveCamera(position=[0, 0, 3], fov=50)
        cube = p3.Mesh(p3.BoxGeometry(1, 1, 1), p3.MeshBasicMaterial(color="red"))
        sc.add(cube)
        controls = p3.OrbitControls(controlling=camera)
        return p3.Renderer(scene=sc, camera=camera, controls=[controls])

    @render.text
    def camera():
        cam = scene.camera()
        return ",".join(f"{v:.3f}" for v in cam.position)


app = App(app_ui, server)
