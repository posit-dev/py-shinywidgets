import pythreejs as p3
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_pythreejs

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Orbit, then save a viewpoint")

        @render_pythreejs
        def scene():
            cube = p3.Mesh(p3.BoxGeometry(1, 1, 1), p3.MeshStandardMaterial(color="#9467bd"))
            sc = p3.Scene(background="#101014", children=[cube, p3.AmbientLight(intensity=0.9)])
            camera = p3.PerspectiveCamera(position=[0, 0, 3.5], fov=50)
            controls = p3.OrbitControls(controlling=camera)
            return p3.Renderer(scene=sc, camera=camera, controls=[controls])

    with ui.card():
        ui.input_action_button("save", "Save viewpoint")
        ui.input_action_button("restore", "Restore viewpoint")

        @render.code
        def saved_txt():
            snap = saved.get()
            if snap is None:
                return "no saved viewpoint yet"
            pos, _quat, _zoom = snap
            return f"saved position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})"


saved = reactive.value(None)


@reactive.effect
@reactive.event(input.save)
def _save():
    # camera() returns the live Camera; snapshot the pieces we want to
    # restore later rather than keeping the object itself
    cam = scene.camera()
    saved.set((tuple(cam.position), tuple(cam.quaternion), cam.zoom))


@reactive.effect
@reactive.event(input.restore)
def _restore():
    snap = saved.get()
    if snap is None:
        return
    pos, quat, zoom = snap
    with reactive.isolate():
        camera = scene.widget.camera
    # In-place assignment, not a re-render: OrbitControls keeps working from
    # the restored pose
    camera.position = pos
    camera.quaternion = quat
    camera.zoom = zoom
