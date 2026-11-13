import numpy as np
import pythreejs as p3
from shiny.express import input, ui
from shinywidgets import render_pythreejs

ui.page_opts(fillable=True)
ui.input_slider("freq", "Ripple frequency", 1, 6, 2, step=0.5)


def surface_geometry(freq: float, n: int = 60) -> p3.BufferGeometry:
    x, y = np.meshgrid(np.linspace(-3, 3, n), np.linspace(-3, 3, n))
    r = np.sqrt(x**2 + y**2)
    z = np.sin(freq * r) / (1 + r)
    zmin, zmax = z.min(), z.max()

    # One triangle pair (6 vertices) per grid cell -- a non-indexed
    # BufferGeometry, so there's no separate index buffer to build
    verts, colors = [], []
    for i in range(n - 1):
        for j in range(n - 1):
            for ii, jj in [(i, j), (i + 1, j), (i, j + 1), (i + 1, j), (i + 1, j + 1), (i, j + 1)]:
                verts.append([x[ii, jj], y[ii, jj], z[ii, jj]])
                t = (z[ii, jj] - zmin) / (zmax - zmin)
                colors.append([0.15 + 0.7 * t, 0.25 + 0.3 * (1 - t), 0.85 - 0.6 * t])

    geometry = p3.BufferGeometry(
        attributes={
            "position": p3.BufferAttribute(np.array(verts, dtype=np.float32)),
            "color": p3.BufferAttribute(np.array(colors, dtype=np.float32)),
        }
    )
    geometry.exec_three_obj_method("computeVertexNormals")
    return geometry


with ui.card(full_screen=True):

    @render_pythreejs
    def scene():
        mesh = p3.Mesh(
            surface_geometry(input.freq()),
            p3.MeshStandardMaterial(vertexColors="VertexColors", side="DoubleSide"),
        )
        sc = p3.Scene(background="#101014", children=[mesh, p3.AmbientLight(intensity=0.8)])
        camera = p3.PerspectiveCamera(position=[4, 4, 4], up=[0, 0, 1])
        controls = p3.OrbitControls(controlling=camera)
        return p3.Renderer(scene=sc, camera=camera, controls=[controls])
