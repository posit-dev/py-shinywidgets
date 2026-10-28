from __future__ import annotations

import pythreejs as p3
from shiny import App, ui
from shinywidgets import output_widget, render_widget, shared_lifetime

app_ui = ui.page_fluid(
    ui.card(output_widget("explicit_light"), height="320px"),
)

with shared_lifetime():
    # The documented remedy for the shared-lifetime + pythreejs limitation:
    # an explicit target (added to the scene) and shadow, constructed inside
    # shared_lifetime() so every session has them
    target = p3.Object3D()
    scene = p3.Scene()
    camera = p3.PerspectiveCamera(position=[0, 0, 3], fov=50)
    cube = p3.Mesh(p3.BoxGeometry(1, 1, 1), p3.MeshBasicMaterial(color="red"))
    light = p3.DirectionalLight(
        position=[3, 5, 2],
        target=target,
        shadow=p3.DirectionalLightShadow(
            camera=p3.OrthographicCamera(-5, 5, 5, -5, 0.1, 100)
        ),
    )
    scene.add([cube, light, target])
    controls = p3.OrbitControls(controlling=camera)
    RENDERER = p3.Renderer(scene=scene, camera=camera, controls=[controls])


def server(input, output, session):
    @render_widget
    def explicit_light():
        return RENDERER


app = App(app_ui, server)
