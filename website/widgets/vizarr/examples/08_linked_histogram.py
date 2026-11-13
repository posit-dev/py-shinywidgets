# A live histogram of the pixels currently in view. vizarr only ever shows
# you pixels -- it has no notion of "the data under the viewport" -- but
# Python already holds the source array, so cropping it to the current
# `view_state` and summarizing it is just numpy, recomputed every time the
# camera settles (vizarr debounces `view_state` to ~200ms).
import tempfile

import matplotlib.pyplot as plt
import numpy as np
import vizarr
import zarr
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

ui.page_opts(title="vizarr: viewport histogram", fillable=True)
CANVAS_PX = 700  # approximate on-screen width of the viewer card, in pixels

with ui.layout_columns(col_widths=(8, 4)):

    with ui.card(full_screen=True):

        @render_vizarr
        def viewer():
            v = vizarr.Viewer()
            v.add_image(source=grp, name="nuclei")
            return v

    with ui.card():
        ui.card_header("Intensity histogram (pixels in view)")

        @render.plot
        def histogram():
            vs = viewer.read("view_state")
            req(vs)
            target = vs.get("target", [n / 2, n / 2])
            half_width = (CANVAS_PX / 2) / (2 ** vs.get("zoom", 0))

            x0, x1 = np.clip([target[0] - half_width, target[0] + half_width], 0, n).astype(int)
            y0, y1 = np.clip([target[1] - half_width, target[1] + half_width], 0, n).astype(int)
            crop = image[y0:y1, x0:x1]

            fig, ax = plt.subplots(figsize=(3.3, 2.6))
            if crop.size:
                ax.hist(crop.ravel(), bins=32, range=(0, 255), color="#2ca02c")
            ax.set_xlabel("pixel intensity")
            ax.set_ylabel("count")
            fig.tight_layout()
            return fig
