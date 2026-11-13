# A channel's contrast/color/visibility is fixed when its layer is added --
# vizarr's browser code never updates an already-added layer, only appends new
# ones (see the previous example). So a Shiny input that controls an
# *existing* channel (here, a contrast slider) has to rebuild the viewer: the
# render function reruns and returns a fresh `vizarr.Viewer()`, with the
# channel's `window` taken from the current slider value.
#
# Unlike the add-a-layer case, the camera can't be reliably carried across
# this kind of re-render: vizarr's deck.gl view always re-fits itself to the
# whole image on mount and reports that back to Python a moment later,
# racing (and often beating) any `view_state` you restore. See "Gotchas and
# limitations" for details -- a contrast/channel control like this one is
# simplest to accept as a full reset of the camera.
import tempfile

import numpy as np
import vizarr
import zarr
from shiny.express import input, ui

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

ui.page_opts(title="vizarr: contrast slider (re-render)", fillable=True)

ui.input_slider("max_contrast", "Contrast ceiling", min=40, max=255, value=255, step=5)

with ui.card(full_screen=True):

    @render_vizarr
    def viewer():
        grp.attrs["omero"] = {
            "channels": [
                {
                    "color": "44FF88",
                    "label": "nuclei",
                    "active": True,
                    "window": {"start": 0, "end": input.max_contrast()},
                }
            ]
        }
        v = vizarr.Viewer()
        v.add_image(source=grp, name="nuclei")
        return v
