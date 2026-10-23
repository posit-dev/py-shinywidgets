from __future__ import annotations

import pythreejs as p3
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_pythreejs

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("camera"),
    ui.card(output_widget("fill_scene"), id="fill_card", height="420px"),
    output_widget("fixed_scene"),
    output_widget("sized_output", height="250px"),
    # Content-derived heights: these containers are only as tall as the canvas
    # inside them
    output_widget("unfillable_scene"),
    ui.card(output_widget("unfillable_card_scene")),
)


def make_renderer(**kwargs) -> p3.Renderer:
    scene = p3.Scene()
    # Default camera looks down -z, so a cube at the origin is in view
    camera = p3.PerspectiveCamera(position=[0, 0, 3], fov=50)
    cube = p3.Mesh(p3.BoxGeometry(1, 1, 1), p3.MeshBasicMaterial(color="red"))
    scene.add(cube)
    controls = p3.OrbitControls(controlling=camera)
    return p3.Renderer(scene=scene, camera=camera, controls=[controls], **kwargs)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_pythreejs
    def fill_scene():
        counter.get()
        return make_renderer()

    @render_pythreejs
    def fixed_scene():
        return make_renderer(width=400, height=300)

    @render_pythreejs
    def sized_output():
        return make_renderer()

    @render_pythreejs
    def unfillable_scene():
        return make_renderer()

    @render_pythreejs
    def unfillable_card_scene():
        return make_renderer()

    @render.text
    def camera():
        return str(reactive_read(fill_scene.widget.camera, "position"))


app = App(app_ui, server)
