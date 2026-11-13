# A local, synthetic 3-channel OME-Zarr store. The colors and contrast limits
# come entirely from the store's own OME-NGFF "omero" metadata -- vizarr reads
# that convention automatically, the same way it would for a real microscope's
# export. shinywidgets serves this store's chunks to the browser on demand
# over the Shiny comm (base64-encoded; prefer a remote URL for large images).
import tempfile

import numpy as np
import vizarr
import zarr
from shiny.express import ui

from shinywidgets import render_vizarr

rng = np.random.default_rng(42)
n = 512
yy, xx = np.mgrid[0:n, 0:n]
nuclei = np.zeros((n, n), np.float32)
for _ in range(250):
    cy, cx, r = rng.integers(15, n - 15, 3)
    nuclei += rng.uniform(140, 240) * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * max(3, r % 8) ** 2))
cytoplasm = 25 + 18 * np.sin(xx / 65) * np.cos(yy / 55) + 0.35 * nuclei
vessels = 200 * np.abs(np.sin((xx + 2 * yy) / 75)) ** 64 * 255
image = np.stack([nuclei, cytoplasm, vessels]).clip(0, 255).astype(np.uint8)

grp = zarr.open_group(f"{tempfile.mkdtemp()}/tissue.zarr", mode="w")
_ = grp.create_dataset("0", data=image[None, :, None, :, :], chunks=(1, 1, 1, 256, 256))
grp.attrs["multiscales"] = [{"version": "0.1", "datasets": [{"path": "0"}]}]
grp.attrs["omero"] = {
    "channels": [
        {"color": "4488FF", "window": {"start": 0, "end": 255}, "label": "DAPI", "active": True},
        {"color": "44FF44", "window": {"start": 0, "end": 255}, "label": "Cytoplasm", "active": True},
        {"color": "FF4444", "window": {"start": 0, "end": 255}, "label": "Vessels", "active": True},
    ],
    "rdefs": {"model": "color"},
}

ui.page_opts(title="vizarr: multichannel contrast and colors", fillable=True)

with ui.card(full_screen=True):

    @render_vizarr
    def viewer():
        v = vizarr.Viewer()
        v.add_image(source=grp, name="synthetic tissue")
        return v
