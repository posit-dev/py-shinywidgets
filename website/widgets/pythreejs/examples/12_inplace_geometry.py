import numpy as np
import pythreejs as p3
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_pythreejs

ui.page_opts(fillable=True)
ui.input_action_button("bump", "Randomize amplitude")

N = 30
x, y = np.meshgrid(np.linspace(-3, 3, N), np.linspace(-3, 3, N))


def positions(amplitude: float) -> np.ndarray:
    r = np.sqrt(x**2 + y**2)
    z = amplitude * np.sin(r) / (1 + r)
    verts = []
    for i in range(N - 1):
        for j in range(N - 1):
            for ii, jj in [(i, j), (i + 1, j), (i, j + 1), (i + 1, j), (i + 1, j + 1), (i, j + 1)]:
                verts.append([x[ii, jj], y[ii, jj], z[ii, jj]])
    return np.array(verts, dtype=np.float32)


position_attr = p3.BufferAttribute(positions(1.0))

with ui.card(full_screen=True):

    @render_pythreejs
    def scene():
        geometry = p3.BufferGeometry(attributes={"position": position_attr})
        mesh = p3.Mesh(geometry, p3.MeshStandardMaterial(color="#2ca02c", side="DoubleSide"))
        sc = p3.Scene(background="#101014", children=[mesh, p3.AmbientLight(intensity=0.9)])
        camera = p3.PerspectiveCamera(position=[4, 4, 4], up=[0, 0, 1])
        controls = p3.OrbitControls(controlling=camera)
        return p3.Renderer(scene=sc, camera=camera, controls=[controls])


# Reassigning the existing BufferAttribute's array updates the mesh in place:
# no re-render, so the orbit position above is preserved
@reactive.effect
@reactive.event(input.bump)
def _():
    position_attr.array = positions(np.random.uniform(0.3, 2.5))
