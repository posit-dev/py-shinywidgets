import pythreejs as p3
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_pythreejs

# Geometry factories: like all pythreejs objects, geometries are widgets, so
# they must be constructed inside the render function (per session), not
# shared at module level
GEOMETRIES = {
    "Box": lambda: p3.BoxGeometry(1, 1, 1),
    "Sphere": lambda: p3.SphereGeometry(0.8, widthSegments=32, heightSegments=16),
    "Torus knot": lambda: p3.TorusKnotGeometry(0.6, 0.2, 128, 16),
}

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("shape", "Shape", list(GEOMETRIES)),
            ui.input_select("color", "Color", ["#d62728", "#1f77b4", "#2ca02c", "#9467bd"]),
            ui.output_text("camera", inline=True),
        ),
        ui.card(
            ui.card_header("Drag to orbit, scroll to zoom"),
            output_widget("scene"),
            full_screen=True,
        ),
    ),
)


def make_scene(shape: str, color: str) -> p3.Renderer:
    # Give the light an explicit target (added to the scene) and shadow (with
    # a camera): pythreejs creates defaults for them browser-side otherwise,
    # and browser-created widgets don't sync back to Python (server-side
    # TraitErrors on every render)
    light = p3.DirectionalLight(position=[3, 5, 2])
    light.target = p3.Object3D()
    light.shadow = p3.DirectionalLightShadow(camera=p3.OrthographicCamera())
    scene = p3.Scene(
        children=[
            p3.Mesh(
                GEOMETRIES[shape](),
                p3.MeshStandardMaterial(color=color, roughness=0.4),
            ),
            light,
            light.target,
            p3.AmbientLight(intensity=0.5),
        ]
    )
    camera = p3.PerspectiveCamera(position=[0, 0, 3.5], fov=50)
    controls = p3.OrbitControls(controlling=camera)
    return p3.Renderer(scene=scene, camera=camera, controls=[controls])


def server(input, output, session):
    @render_pythreejs
    def scene():
        return make_scene(input.shape(), input.color())

    @render.text
    def camera():
        pos = reactive_read(scene.widget.camera, "position")
        return f"Camera: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})"


app = App(app_ui, server)
