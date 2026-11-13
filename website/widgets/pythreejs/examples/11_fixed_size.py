import pythreejs as p3
from shiny.express import ui
from shinywidgets import render_pythreejs

ui.page_opts(fillable=True)

with ui.card(height="450px"):

    @render_pythreejs
    def scene():
        cube = p3.Mesh(p3.BoxGeometry(1, 1, 1), p3.MeshStandardMaterial(color="#ff7f0e"))
        sc = p3.Scene(background="#101014", children=[cube, p3.AmbientLight(intensity=0.9)])
        camera = p3.PerspectiveCamera(position=[0, 0, 3.5], aspect=1)
        controls = p3.OrbitControls(controlling=camera)
        # An explicit width/height opts out of fill: the canvas keeps this
        # pixel size regardless of the surrounding card
        return p3.Renderer(scene=sc, camera=camera, controls=[controls], width=300, height=300)
