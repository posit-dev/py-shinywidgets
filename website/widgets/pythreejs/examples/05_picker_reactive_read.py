import pythreejs as p3
from shiny.express import render, ui
from shinywidgets import reactive_read, render_pythreejs

ui.page_opts(fillable=True)

mesh = p3.Mesh(p3.TorusKnotGeometry(0.6, 0.2, 128, 16), p3.MeshStandardMaterial(color="#2ca02c"))
# `Picker.object` resolves to the live Mesh widget it hit, since the mesh was
# built in Python (unlike a light's auto-created target/shadow, which only
# exist in the browser -- see Gotchas and limitations)
picker = p3.Picker(controlling=mesh, event="click")

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Click the shape")

        @render_pythreejs
        def scene():
            sc = p3.Scene(background="#101014", children=[mesh, p3.AmbientLight(intensity=0.9)])
            camera = p3.PerspectiveCamera(position=[0, 0, 3.5], fov=50)
            controls = p3.OrbitControls(controlling=camera)
            return p3.Renderer(scene=sc, camera=camera, controls=[controls, picker])

    with ui.card():
        ui.card_header("Pick detail")

        @render.code
        def pick_detail():
            # pythreejs has no "clicked" accessor; reactive_read() on the
            # Picker's traits is the way to read interaction here. `distance`
            # is None until the first click (and again whenever the last
            # raycast misses, e.g. right after an orbit moves the shape away
            # from the cursor) -- use it as the readiness sentinel.
            distance = reactive_read(picker, "distance")
            if distance is None:
                return "click the shape"
            point = picker.point
            return f"distance: {distance:.3f}\npoint: ({point[0]:.2f}, {point[1]:.2f}, {point[2]:.2f})"
