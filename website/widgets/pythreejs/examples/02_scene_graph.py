import pythreejs as p3
from shiny.express import input, render, ui
from shinywidgets import reactive_read, render_pythreejs

GEOMETRIES = {
    "Box": lambda: p3.BoxGeometry(1, 1, 1),
    "Sphere": lambda: p3.SphereGeometry(0.8, widthSegments=32, heightSegments=16),
    "Torus knot": lambda: p3.TorusKnotGeometry(0.6, 0.2, 128, 16),
}
COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd"]

ui.page_opts(fillable=True)

with ui.layout_sidebar():
    with ui.sidebar():
        ui.input_select("shape", "Shape", list(GEOMETRIES))
        ui.input_select("color", "Color", COLORS)

        @render.text
        def camera_txt():
            pos = reactive_read(scene.widget.camera, "position")
            return f"Camera: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})"

    with ui.card(full_screen=True):
        ui.card_header("Drag to orbit, scroll to zoom")

        @render_pythreejs
        def scene():
            # Each piece of the scene graph -- mesh, geometry, material,
            # light, camera, controls -- is its own widget; build them inside
            # the render function so each session gets its own instances
            light = p3.DirectionalLight(position=[3, 5, 2])
            light.target = p3.Object3D()
            light.shadow = p3.DirectionalLightShadow(camera=p3.OrthographicCamera())

            mesh = p3.Mesh(
                GEOMETRIES[input.shape()](),
                p3.MeshStandardMaterial(color=input.color(), roughness=0.4),
            )
            sc = p3.Scene(
                background="#101014",
                children=[mesh, light, light.target, p3.AmbientLight(intensity=0.5)],
            )
            camera = p3.PerspectiveCamera(position=[0, 0, 3.5], fov=50)
            controls = p3.OrbitControls(controlling=camera)
            return p3.Renderer(scene=sc, camera=camera, controls=[controls])
