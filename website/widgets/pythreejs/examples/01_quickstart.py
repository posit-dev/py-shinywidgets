import pythreejs as p3
from shiny.express import ui
from shinywidgets import render_pythreejs

ui.page_opts(fillable=True)

with ui.card(full_screen=True):

    @render_pythreejs
    def scene():
        cube = p3.Mesh(p3.BoxGeometry(1, 1, 1), p3.MeshStandardMaterial(color="#d62728"))

        # Give the light an explicit target (added to the scene) and shadow
        # (with a camera): pythreejs creates both in the browser otherwise,
        # which logs a harmless console error on every re-render (see
        # Gotchas and limitations)
        light = p3.DirectionalLight(position=[3, 5, 2])
        light.target = p3.Object3D()
        light.shadow = p3.DirectionalLightShadow(camera=p3.OrthographicCamera())

        # Scene.background defaults to white and paints over the renderer's
        # clear color, so set it here for a dark viewport
        sc = p3.Scene(
            background="#101014",
            children=[cube, light, light.target, p3.AmbientLight(intensity=0.5)],
        )
        camera = p3.PerspectiveCamera(position=[0, 0, 3.5], fov=50)
        controls = p3.OrbitControls(controlling=camera)
        return p3.Renderer(scene=sc, camera=camera, controls=[controls])
