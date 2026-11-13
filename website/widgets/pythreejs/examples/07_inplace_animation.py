import math

import pythreejs as p3
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_pythreejs

ui.page_opts(fillable=True)


def quat_mul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float, float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


with ui.card(full_screen=True):

    @render_pythreejs
    def scene():
        mesh = p3.Mesh(
            p3.TorusKnotGeometry(0.6, 0.2, 128, 16), p3.MeshStandardMaterial(color="#ff7f0e")
        )
        sc = p3.Scene(background="#101014", children=[mesh, p3.AmbientLight(intensity=0.9)])
        camera = p3.PerspectiveCamera(position=[0, 0, 3.5])
        controls = p3.OrbitControls(controlling=camera)
        return p3.Renderer(scene=sc, camera=camera, controls=[controls])

    # pythreejs's `rotation` (Euler) trait doesn't render (an upstream bug --
    # see Gotchas and limitations); animate the `quaternion` instead.
    # OrbitControls(autoRotate=True) is also inert upstream, so a Python timer
    # is the only way to get a continuous spin.
    @reactive.effect
    def _():
        reactive.invalidate_later(1 / 30)
        with reactive.isolate():
            mesh = scene.widget.scene.children[0]
        dq = (0.0, math.sin(0.01), 0.0, math.cos(0.01))
        mesh.quaternion = quat_mul(dq, mesh.quaternion)
