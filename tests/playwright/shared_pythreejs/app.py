from __future__ import annotations

import pythreejs as p3
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget, shared_lifetime

app_ui = ui.page_fluid(
    ui.output_text("light_state"),
    ui.card(output_widget("default_light"), height="320px"),
    ui.card(output_widget("explicit_light"), height="320px"),
)


def make_renderer(light: p3.Light) -> p3.Renderer:
    scene = p3.Scene()
    camera = p3.PerspectiveCamera(position=[0, 0, 3], fov=50)
    cube = p3.Mesh(p3.BoxGeometry(1, 1, 1), p3.MeshBasicMaterial(color="red"))
    scene.add([cube, light])
    controls = p3.OrbitControls(controlling=camera)
    return p3.Renderer(scene=scene, camera=camera, controls=[controls])


with shared_lifetime():
    # The light's target/shadow are left at pythreejs's defaults, which its
    # JavaScript creates in whichever browser renders first
    DEFAULT_LIGHT = p3.DirectionalLight(position=[3, 5, 2])
    DEFAULT_RENDERER = make_renderer(DEFAULT_LIGHT)

    # The documented remedy: an explicit target (added to the scene) and
    # shadow, built inside shared_lifetime() so every session has them
    target = p3.Object3D()
    EXPLICIT_RENDERER = make_renderer(
        p3.DirectionalLight(
            position=[3, 5, 2],
            target=target,
            shadow=p3.DirectionalLightShadow(
                camera=p3.OrthographicCamera(-5, 5, 5, -5, 0.1, 100)
            ),
        )
    )
    EXPLICIT_RENDERER.scene.add(target)


def server(input, output, session):
    @render_widget
    def default_light():
        return DEFAULT_RENDERER

    @render_widget
    def explicit_light():
        return EXPLICIT_RENDERER

    # The Python side of the shared light's target/shadow: 'uninitialized'
    # until some browser's JavaScript creates them, then the model id that
    # browser gave them (visible to no other session)
    @render.text
    def light_state():
        reactive.invalidate_later(1)

        def describe(w: object) -> str:
            comm = getattr(w, "comm", None)
            if comm is None:
                return type(w).__name__
            return f"{type(w).__name__}:{comm.comm_id}"

        return (
            f"target={describe(DEFAULT_LIGHT.target)} "
            f"shadow={describe(DEFAULT_LIGHT.shadow)}"
        )


app = App(app_ui, server)
