import pythreejs as p3
from shiny import reactive
from shiny.express import ui
from shinywidgets import reactive_read, render_pythreejs

ui.page_opts(fillable=True)

terrain = p3.Mesh(p3.SphereGeometry(1.2, 48, 32), p3.MeshStandardMaterial(color="#1f77b4", roughness=0.6))
marker = p3.Mesh(p3.SphereGeometry(0.06, 16, 16), p3.MeshBasicMaterial(color="#ffdd00"))
marker.visible = False
picker = p3.Picker(controlling=terrain, event="click")

with ui.card(full_screen=True):
    ui.card_header("Click the sphere to drop a marker")

    @render_pythreejs
    def scene():
        sc = p3.Scene(background="#101014", children=[terrain, marker, p3.AmbientLight(intensity=0.9)])
        camera = p3.PerspectiveCamera(position=[0, 0, 4], fov=50)
        controls = p3.OrbitControls(controlling=camera)
        return p3.Renderer(scene=sc, camera=camera, controls=[controls, picker])


# The Picker (an input into Python) and the marker (an in-place update back
# into the same scene) are two independent widgets -- this is the 3D
# equivalent of "table row selection highlights a point in a plot"
@reactive.effect
def _place_marker():
    distance = reactive_read(picker, "distance")
    if distance is None:
        return
    point = picker.point
    marker.position = point
    marker.visible = True
