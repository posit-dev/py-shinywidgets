from __future__ import annotations

import pythreejs as p3
from shiny import App, reactive, render, ui
from shinywidgets import (
    output_widget,
    reactive_read,
    render_pythreejs,
    session_lifetime,
)

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_action_button("swap_camera", "Swap camera"),
    ui.input_action_button("set_aspect", "Set aspect"),
    ui.output_text("render_count"),
    ui.output_text("camera"),
    ui.output_text("camera_aspect"),
    ui.output_text("swapped_camera_aspect"),
    ui.output_text("cached_camera_aspect"),
    ui.card(output_widget("fill_scene"), id="fill_card", height="420px"),
    ui.card(output_widget("cached_scene"), id="cached_card", height="300px"),
    output_widget("fixed_scene"),
    output_widget("sized_output", height="250px"),
    # Non-fillable outputs: one unsized (keeps the widget's own size), one
    # with an explicit height (canvas sized to it)
    output_widget("nonfillable_scene", fillable=False),
    output_widget("sized_nonfillable", height="250px", fillable=False),
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

    # Constructed once per session and returned again on every re-render
    # (the session_lifetime() cache Copilot's sizing-intent scenario uses)
    cached_renderer = None

    @render_pythreejs
    def cached_scene():
        counter.get()
        nonlocal cached_renderer
        if cached_renderer is None:
            with session_lifetime():
                cached_renderer = make_renderer()
        return cached_renderer

    swapped_cameras: list[p3.PerspectiveCamera] = []
    swap_count = reactive.value(0)

    @reactive.effect
    @reactive.event(input.swap_camera)
    def _():
        swapped_cameras.append(fill_scene.widget.camera)
        fill_scene.widget.camera = p3.PerspectiveCamera(position=[0, 0, 3], fov=50)
        swap_count.set(swap_count.get() + 1)

    @reactive.effect
    @reactive.event(input.set_aspect)
    def _():
        # An explicit user aspect must survive re-renders of the cached
        # Renderer (1.5 is far from the output's container ratio)
        cached_scene.widget.camera.aspect = 1.5

    @render_pythreejs
    def fixed_scene():
        return make_renderer(width=400, height=300)

    @render_pythreejs
    def sized_output():
        return make_renderer()

    @render_pythreejs
    def nonfillable_scene():
        return make_renderer()

    @render_pythreejs
    def sized_nonfillable():
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

    @render.text
    def camera_aspect():
        cam = reactive_read(fill_scene.widget, "camera")
        return f"{reactive_read(cam, 'aspect'):.4f}"

    @render.text
    def swapped_camera_aspect():
        swap_count.get()
        if not swapped_cameras:
            return ""
        return f"{reactive_read(swapped_cameras[0], 'aspect'):.4f}"

    @render.text
    def cached_camera_aspect():
        cam = reactive_read(cached_scene.widget, "camera")
        return f"{reactive_read(cam, 'aspect'):.4f}"


app = App(app_ui, server)
