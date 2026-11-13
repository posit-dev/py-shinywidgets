import pythreejs as p3
from shiny.express import render, ui
from shinywidgets import render_pythreejs

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Drag to orbit")

        @render_pythreejs
        def scene():
            cube = p3.Mesh(p3.BoxGeometry(1, 1, 1), p3.MeshStandardMaterial(color="#1f77b4"))
            sc = p3.Scene(background="#101014", children=[cube, p3.AmbientLight(intensity=0.9)])
            camera = p3.PerspectiveCamera(position=[0, 0, 3.5], fov=50)
            controls = p3.OrbitControls(controlling=camera)
            return p3.Renderer(scene=sc, camera=camera, controls=[controls])

    with ui.card():
        ui.card_header("scene.camera()")

        @render.code
        def camera_state():
            # Re-runs every time the user finishes an orbit drag. Before the
            # first orbit this reports the camera as constructed in Python
            # (pythreejs doesn't sync it at mount).
            cam = scene.camera()
            pos = ", ".join(f"{v:.2f}" for v in cam.position)
            quat = ", ".join(f"{v:.2f}" for v in cam.quaternion)
            return f"position: ({pos})\nquaternion: ({quat})\nzoom: {cam.zoom:.2f}"
