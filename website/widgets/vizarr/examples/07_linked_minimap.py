# The viewport you're looking at, drawn on a minimap of the whole image.
# `viewer.read("view_state")` is the only interaction state vizarr exposes
# (no accessors; it falls through to reactive_read() on the rendered
# widget), but it's enough to keep a second view in sync: `zoom` follows
# deck.gl's convention (screen pixels per image pixel is 2 ** zoom), so the
# viewport's image-space half-width is derived from the card's pixel size
# and the current zoom.
import tempfile

import matplotlib.pyplot as plt
import numpy as np
import vizarr
import zarr
from matplotlib.patches import Rectangle
from shiny import req
from shiny.express import render, ui

from shinywidgets import render_vizarr

rng = np.random.default_rng(1)
n = 512
yy, xx = np.mgrid[0:n, 0:n]
nuclei = np.zeros((n, n), np.float32)
for _ in range(250):
    cy, cx, r = rng.integers(15, n - 15, 3)
    nuclei += rng.uniform(140, 240) * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * max(3, r % 8) ** 2))
image = nuclei.clip(0, 255).astype(np.uint8)

grp = zarr.open_group(f"{tempfile.mkdtemp()}/nuclei.zarr", mode="w")
_ = grp.create_dataset("0", data=image[None, None, None, :, :], chunks=(1, 1, 1, 256, 256))
grp.attrs["multiscales"] = [{"version": "0.1", "datasets": [{"path": "0"}]}]

ui.page_opts(title="vizarr: viewport minimap", fillable=True)
CANVAS_PX = 700  # approximate on-screen width of the viewer card, in pixels

with ui.layout_columns(col_widths=(8, 4)):

    with ui.card(full_screen=True):

        @render_vizarr
        def viewer():
            v = vizarr.Viewer()
            v.add_image(source=grp, name="nuclei")
            return v

    with ui.card():
        ui.card_header("Minimap")

        @render.plot
        def minimap():
            vs = viewer.read("view_state")
            req(vs)
            target = vs.get("target", [n / 2, n / 2])
            half_width = (CANVAS_PX / 2) / (2 ** vs.get("zoom", 0))

            fig, ax = plt.subplots(figsize=(3, 3))
            ax.imshow(image, cmap="gray", vmin=0, vmax=255)
            ax.add_patch(
                Rectangle(
                    (target[0] - half_width, target[1] - half_width),
                    2 * half_width,
                    2 * half_width,
                    fill=False,
                    edgecolor="red",
                    linewidth=2,
                )
            )
            ax.set_xticks([])
            ax.set_yticks([])
            return fig
