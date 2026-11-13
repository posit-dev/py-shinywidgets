# Scene explorer -- a small, adaptable pythreejs starting point
# Swap in your own geometry/material; the lighting, OrbitControls, Picker, and
# camera() readout are the reusable parts.
# bucket: template
# run: uv run --no-sync shiny run docs/widget-guides/pythreejs/gallery/template_scene_explorer.py
# data: none (procedural geometry)

import pythreejs as p3
from shiny.express import input, render, ui
from shinywidgets import output_widget, reactive_read, render_pythreejs

GEOMETRIES = {
    "Box": lambda: p3.BoxGeometry(1, 1, 1),
    "Sphere": lambda: p3.SphereGeometry(0.8, 32, 16),
    "Torus knot": lambda: p3.TorusKnotGeometry(0.6, 0.2, 128, 16),
    "Cone": lambda: p3.ConeGeometry(0.8, 1.4, 32),
}

ui.page_opts(title="pythreejs scene explorer", fillable=True)

# A single Picker, re-targeted at the current mesh on every render (so the
# sidebar readout below can reference it regardless of render order). Picker
# requires a real `controlling` object at construction; retargeted below.
picker = p3.Picker(controlling=p3.Object3D(), event="click")

with ui.layout_sidebar():
    with ui.sidebar():
        ui.input_select("shape", "Shape", list(GEOMETRIES))
        ui.input_select(
            "color", "Color", ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e"]
        )
        ui.input_switch("wireframe", "Wireframe", value=False)

        @render.code
        def pick_or_camera():
            # The Picker tells you *what* was clicked; camera() tells you
            # *where you're looking*. Both are read-only reactive state.
            distance = reactive_read(picker, "distance")
            if distance is not None:
                return f"picked at distance {distance:.2f}"
            cam = scene.camera()
            pos = ", ".join(f"{v:.2f}" for v in cam.position)
            return f"camera: ({pos})"

    with ui.card(full_screen=True):
        ui.card_header("Drag to orbit, click the shape")

        @render_pythreejs
        def scene():
            mesh = p3.Mesh(
                GEOMETRIES[input.shape()](),
                p3.MeshStandardMaterial(
                    color=input.color(), roughness=0.4, wireframe=input.wireframe()
                ),
            )
            light = p3.DirectionalLight(position=[3, 5, 2])
            light.target = p3.Object3D()
            light.shadow = p3.DirectionalLightShadow(camera=p3.OrthographicCamera())
            sc = p3.Scene(
                background="#101014",
                children=[mesh, light, light.target, p3.AmbientLight(intensity=0.5)],
            )
            camera = p3.PerspectiveCamera(position=[0, 0, 3.5], fov=50)
            controls = p3.OrbitControls(controlling=camera)
            picker.controlling = mesh
            return p3.Renderer(scene=sc, camera=camera, controls=[controls, picker])
