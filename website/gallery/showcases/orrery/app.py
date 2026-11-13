# Orrery -- an animated multi-body scene exercising every pythreejs
# integration point at once: in-place position updates on a timer, a Picker
# shared across several meshes, and in-place `.widget.camera` mutation for a
# "home view" button.
# bucket: showcase
# Run: uv run shiny run app.py
# data: none (procedural orbits; radii/periods are illustrative, not to scale)

import math

import pythreejs as p3
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import reactive_read, render_pythreejs

# name -> (orbit radius, orbit period in seconds at speed=1, body radius, color)
BODIES = {
    "Mercury": (1.6, 4, 0.12, "#9c9c9c"),
    "Venus": (2.3, 7, 0.18, "#d9b38c"),
    "Earth": (3.0, 10, 0.2, "#2a6fdb"),
    "Mars": (3.8, 16, 0.16, "#c1440e"),
}

ui.page_opts(title="pythreejs orrery", fillable=True)

sun = p3.Mesh(p3.SphereGeometry(0.5, 32, 16), p3.MeshBasicMaterial(color="#ffcc33"))
planets = {
    name: p3.Mesh(p3.SphereGeometry(r, 24, 16), p3.MeshStandardMaterial(color=color))
    for name, (_, _, r, color) in BODIES.items()
}

light = p3.DirectionalLight(position=[6, 8, 4])
light.target = p3.Object3D()
light.shadow = p3.DirectionalLightShadow(camera=p3.OrthographicCamera())

scene_graph = p3.Scene(
    background="#06060a",
    children=[sun, light, light.target, p3.AmbientLight(intensity=0.35), *planets.values()],
)
# One Picker covering the whole scene graph: `.object` resolves to whichever
# mesh it hit (Picker needs a real `controlling` object at construction)
picker = p3.Picker(controlling=scene_graph, event="click")

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Click a planet; drag to orbit")

        @render_pythreejs
        def scene():
            camera = p3.PerspectiveCamera(position=[0, 6, 9], fov=50)
            controls = p3.OrbitControls(controlling=camera)
            return p3.Renderer(scene=scene_graph, camera=camera, controls=[controls, picker])

    with ui.card():
        ui.input_switch("playing", "Playing", value=True)
        ui.input_slider("speed", "Speed", 0.2, 3, 1, step=0.1)
        ui.input_action_button("home", "Reset view")

        ui.card_header("Picked body")

        @render.code
        def picked():
            distance = reactive_read(picker, "distance")
            if distance is None:
                return "click a planet"
            obj = picker.object
            name = next((n for n, m in planets.items() if m is obj), None)
            if name is None:
                return "clicked the sun"
            radius, period, *_ = BODIES[name]
            return f"{name}\norbit radius: {radius}\norbit period: {period}s at speed 1"


# Simulation clock: advances only while playing, scaled by the speed slider.
# A reactive.value (not a module global) so re-renders don't reset it.
sim_time = reactive.value(0.0)


@reactive.effect
def _advance_clock():
    if not input.playing():
        return
    reactive.invalidate_later(1 / 30)
    with reactive.isolate():
        sim_time.set(sim_time.get() + (1 / 30) * input.speed())


@reactive.effect
def _place_planets():
    t = sim_time.get()
    for name, (radius, period, _, _) in BODIES.items():
        angle = 2 * math.pi * t / period
        planets[name].position = (radius * math.cos(angle), 0, radius * math.sin(angle))


@reactive.effect
@reactive.event(input.home)
def _reset_view():
    with reactive.isolate():
        camera = scene.widget.camera
    camera.position = (0, 6, 9)
    camera.quaternion = (0, 0, 0, 1)
    camera.zoom = 1
