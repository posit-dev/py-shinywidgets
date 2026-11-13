import pythreejs as p3
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_pythreejs

ui.page_opts(fillable=True)

with ui.layout_sidebar():
    with ui.sidebar():
        ui.input_select("color", "Color", ["#d62728", "#1f77b4", "#2ca02c", "#ff7f0e"])
        ui.input_slider("metalness", "Metalness", 0.0, 1.0, 0.2)
        ui.input_slider("roughness", "Roughness", 0.0, 1.0, 0.6)

    with ui.card(full_screen=True):

        @render_pythreejs
        def scene():
            mesh = p3.Mesh(p3.SphereGeometry(0.9, 48, 32), p3.MeshStandardMaterial())
            sc = p3.Scene(background="#101014", children=[mesh, p3.AmbientLight(intensity=0.9)])
            camera = p3.PerspectiveCamera(position=[0, 0, 3])
            controls = p3.OrbitControls(controlling=camera)
            return p3.Renderer(scene=sc, camera=camera, controls=[controls])

        # Material restyling, assigned straight onto the live widget: no
        # re-render, so the orbit/zoom the user left the camera at is kept.
        # reactive.isolate() reads .widget without tying this effect to the
        # render function above (which doesn't depend on these inputs anyway,
        # but isolating is the safe habit once a render function might).
        @reactive.effect
        def _():
            color = input.color()
            metalness = input.metalness()
            roughness = input.roughness()
            with reactive.isolate():
                material = scene.widget.scene.children[0].material
            material.color = color
            material.metalness = metalness
            material.roughness = roughness
