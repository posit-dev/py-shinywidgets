# `.widget.add_image()` appends a new layer to the running viewer: vizarr's
# browser code only ever *adds* layers (there's no "remove" or "replace"), so
# this never rebuilds the viewer or re-sends its JS bundle -- the camera you
# already set stays put. Compare this to a full re-render (next example),
# which always resets the camera unless you restore it yourself.
import tempfile

import numpy as np
import vizarr
import zarr
from shiny import reactive
from shiny.express import input, ui

from shinywidgets import render_vizarr


def single_channel_zarr(data, color):
    grp = zarr.open_group(f"{tempfile.mkdtemp()}/img.zarr", mode="w")
    _ = grp.create_dataset("0", data=data[None, None, None, :, :], chunks=(1, 1, 1, 256, 256))
    grp.attrs["multiscales"] = [{"version": "0.1", "datasets": [{"path": "0"}]}]
    grp.attrs["omero"] = {
        "channels": [{"color": color, "window": {"start": 0, "end": 255}, "active": True}]
    }
    return grp


rng = np.random.default_rng(0)
base = (rng.random((512, 512)) * 180 + 40).astype(np.uint8)
wedge = (np.triu(np.ones((512, 512))) * 220).astype(np.uint8)  # bright triangle

base_store = single_channel_zarr(base, "FFFFFF")
overlay_store = single_channel_zarr(wedge, "FF2222")

ui.page_opts(title="vizarr: add a layer in place", fillable=True)

ui.input_action_button("add", "Add overlay layer (in place)")

with ui.card(full_screen=True):

    @render_vizarr
    def viewer():
        v = vizarr.Viewer()
        v.add_image(source=base_store, name="base")
        return v


@reactive.effect
@reactive.event(input.add)
def _():
    if viewer.widget is not None:
        viewer.widget.add_image(source=overlay_store, name="overlay", opacity=0.5)
