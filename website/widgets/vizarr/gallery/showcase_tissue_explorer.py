# vizarr tissue explorer showcase
# A synthetic 3-channel fluorescence image you can pan and zoom, paired with
# two linked Python-side views that have no equivalent inside vizarr itself:
# a minimap showing where you are in the whole slide, and a live histogram of
# the selected channel's intensities under the current viewport. Both read
# `viewer.read("view_state")` -- vizarr's only synced trait, and its only
# way into this guide's `.read()` fallback tier (no accessors).
# bucket: showcase
# run: uv run --with 'shinywidgets[vizarr]' shiny run showcase_tissue_explorer.py
# data: synthetic 3-channel tissue, generated at startup (no download)
import tempfile

import matplotlib.pyplot as plt
import numpy as np
import vizarr
import zarr
from matplotlib.patches import Rectangle
from shiny import req
from shiny.express import input, render, ui

from shinywidgets import render_vizarr

CHANNEL_NAMES = ["DAPI (nuclei)", "Cytoplasm", "Vessels"]
CHANNEL_COLORS = ["4488FF", "44FF44", "FF4444"]
CANVAS_PX = 760  # approximate on-screen width of the viewer card, in pixels


def synthetic_tissue(n=768):
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:n, 0:n]
    dapi = np.zeros((n, n), np.float32)
    for _ in range(600):
        cy, cx, r = rng.integers(10, n - 10, 3)
        r = max(3, r % 9)
        dapi += rng.uniform(120, 240) * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * r**2))
    cyto = 25 + 18 * np.sin(xx / 110) * np.cos(yy / 95) + 0.35 * dapi
    vessels = 200 * np.abs(np.sin((xx + 2 * yy) / 140)) ** 64 * 255
    return np.stack([dapi, cyto, vessels]).clip(0, 255).astype(np.uint8), n


image, n = synthetic_tissue()

grp = zarr.open_group(f"{tempfile.mkdtemp()}/tissue.zarr", mode="w")
_ = grp.create_dataset("0", data=image[None, :, None, :, :], chunks=(1, 1, 1, 256, 256))
grp.attrs["multiscales"] = [{"version": "0.1", "datasets": [{"path": "0"}]}]
grp.attrs["omero"] = {
    "channels": [
        {"color": c, "label": lbl, "active": True, "window": {"start": 0, "end": 255}}
        for lbl, c in zip(CHANNEL_NAMES, CHANNEL_COLORS)
    ]
}

ui.page_opts(title="vizarr tissue explorer", fillable=True)

with ui.layout_columns(col_widths=(8, 4, 4)):
    with ui.card(full_screen=True, height="520px"):
        ui.card_header("Synthetic 3-channel tissue")

        @render_vizarr
        def viewer():
            v = vizarr.Viewer()
            v.add_image(source=grp, name="tissue")
            return v

    with ui.card(height="520px"):
        ui.card_header("Minimap")
        ui.input_select("mm_channel", "Channel", choices=CHANNEL_NAMES, selected=CHANNEL_NAMES[0])

        @render.plot
        def minimap():
            vs = viewer.read("view_state")
            req(vs)
            chan = image[CHANNEL_NAMES.index(input.mm_channel())]
            target = vs.get("target", [n / 2, n / 2])
            half_width = (CANVAS_PX / 2) / (2 ** vs.get("zoom", 0))

            fig, ax = plt.subplots(figsize=(3.4, 3.4))
            ax.imshow(chan, cmap="gray", vmin=0, vmax=255)
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

    with ui.card(height="520px"):
        ui.card_header("Intensity histogram (pixels in view)")

        @render.plot
        def histogram():
            vs = viewer.read("view_state")
            req(vs)
            chan = image[CHANNEL_NAMES.index(input.mm_channel())]
            target = vs.get("target", [n / 2, n / 2])
            half_width = (CANVAS_PX / 2) / (2 ** vs.get("zoom", 0))

            x0, x1 = np.clip([target[0] - half_width, target[0] + half_width], 0, n).astype(int)
            y0, y1 = np.clip([target[1] - half_width, target[1] + half_width], 0, n).astype(int)
            crop = chan[y0:y1, x0:x1]

            fig, ax = plt.subplots(figsize=(3.4, 3.1))
            if crop.size:
                ax.hist(crop.ravel(), bins=32, range=(0, 255), color="#2ca02c")
            ax.set_xlabel("pixel intensity")
            ax.set_ylabel("count")
            fig.tight_layout()
            return fig
