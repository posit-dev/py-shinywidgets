# vizarr has no accessors (see "Reacting to user interaction" below), but its
# `view_state` trait -- the pan/zoom camera, as {"target": [x, y], "zoom": z}
# -- syncs from the browser whenever you pan or zoom, debounced ~200ms.
# `viewer.read("view_state")` turns that into a reactive input (it falls
# through to reactive_read() on the rendered widget, and cancels on its own
# before the first render -- no manual `viewer.widget is None` check needed).
# Setting `.view_state` from Python flies the camera to a region of interest,
# in place (no re-render).
import tempfile

import numpy as np
import vizarr
import zarr
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_vizarr

rng = np.random.default_rng(42)
n = 512
yy, xx = np.mgrid[0:n, 0:n]
nuclei = np.zeros((n, n), np.float32)
for _ in range(250):
    cy, cx, r = rng.integers(15, n - 15, 3)
    nuclei += rng.uniform(140, 240) * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * max(3, r % 8) ** 2))
image = nuclei.clip(0, 255).astype(np.uint8)[None, None, None, :, :]

grp = zarr.open_group(f"{tempfile.mkdtemp()}/nuclei.zarr", mode="w")
_ = grp.create_dataset("0", data=image, chunks=(1, 1, 1, 256, 256))
grp.attrs["multiscales"] = [{"version": "0.1", "datasets": [{"path": "0"}]}]

ui.page_opts(title="vizarr: reading the camera", fillable=True)

with ui.layout_sidebar():
    with ui.sidebar():
        ui.input_action_button("fly", "Fly to center")

        @render.code
        def camera():
            vs = viewer.read("view_state")
            if not vs:
                return "loading..."
            target = vs.get("target", [0, 0])
            return f"zoom:   {vs.get('zoom', 0):.2f}\ntarget: ({target[0]:.0f}, {target[1]:.0f})"

    with ui.card(full_screen=True):

        @render_vizarr
        def viewer():
            v = vizarr.Viewer()
            v.add_image(source=grp, name="nuclei")
            return v

    @reactive.effect
    @reactive.event(input.fly)
    def _():
        if viewer.widget is not None:
            viewer.widget.view_state = {"target": [256, 256], "zoom": 2.0}
