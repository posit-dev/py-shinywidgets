import pandas as pd
import pythreejs as p3
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import reactive_read, render_pythreejs

ui.page_opts(fillable=True)

box = p3.Mesh(p3.BoxGeometry(1, 1, 1), p3.MeshStandardMaterial(color="#d62728"))
box.position = (-1.2, 0, 0)
sphere = p3.Mesh(p3.SphereGeometry(0.6, 32, 16), p3.MeshStandardMaterial(color="#1f77b4"))
sphere.position = (1.2, 0, 0)
names = {id(box): "box", id(sphere): "sphere"}

scene_group = p3.Scene(background="#101014", children=[box, sphere, p3.AmbientLight(intensity=0.9)])
picker = p3.Picker(controlling=scene_group, event="click")
rows = reactive.value(pd.DataFrame(columns=["object", "x", "y", "z"]))

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click either shape")

        @render_pythreejs
        def scene():
            camera = p3.PerspectiveCamera(position=[0, 0, 5], fov=50)
            controls = p3.OrbitControls(controlling=camera)
            return p3.Renderer(scene=scene_group, camera=camera, controls=[controls, picker])

    with ui.card():
        ui.card_header("Click history")

        @render.data_frame
        def history():
            return render.DataGrid(rows.get())


# Appends to `rows` whenever the Picker reports a new hit; `history()` above
# depends on `rows` (a reactive.value), not on the Picker directly, so the
# table always sees a settled list rather than racing the effect that builds it
@reactive.effect
def _record_pick():
    distance = reactive_read(picker, "distance")
    if distance is None:
        return
    point, obj = picker.point, picker.object
    row = {"object": names.get(id(obj), "?"), "x": round(point[0], 2), "y": round(point[1], 2), "z": round(point[2], 2)}
    with reactive.isolate():
        rows.set(pd.concat([rows.get(), pd.DataFrame([row])], ignore_index=True))
