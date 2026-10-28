import tempfile

import numpy as np
import vizarr
import zarr
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_vizarr

rng = np.random.default_rng(42)


def synthetic_tissue(n=1024):
    """Three fluorescence channels: DAPI-ish nuclei, cytoplasm, vessels."""
    yy, xx = np.mgrid[0:n, 0:n]
    dapi = np.zeros((n, n), np.float32)
    for _ in range(500):  # blobs = cells
        cy, cx, r = rng.integers(15, n - 15, 3)
        r = max(3, r % 8)
        dapi += rng.uniform(120, 240) * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * r**2))
    cyto = 25 + 18 * np.sin(xx / 130) * np.cos(yy / 110) + 0.35 * dapi
    vessels = 200 * np.abs(np.sin((xx + 2 * yy) / 150)) ** 64 * 255
    return np.stack([dapi, cyto, vessels]).clip(0, 255).astype(np.uint8)


def to_ome_zarr(img, path, layers=3):
    """Write a (c, y, x) uint8 image as a 5D multiscale OME-Zarr store."""
    grp = zarr.open_group(path, mode="w")
    paths, cur = [], img
    for lvl in range(layers):
        arr = cur[None, :, None, :, :]  # (t, c, z, y, x)
        grp.create_dataset(str(lvl), data=arr, chunks=(1, 1, 1, 256, 256))
        paths.append({"path": str(lvl)})
        h, w = cur.shape[1] // 2, cur.shape[2] // 2
        cur = cur[:, : 2 * h, : 2 * w].reshape(3, h, 2, w, 2).mean((2, 4)).astype(np.uint8)
    grp.attrs["multiscales"] = [{"version": "0.1", "datasets": paths}]
    grp.attrs["omero"] = {
        "channels": [
            {"color": "4488FF", "window": {"start": 0, "end": 255}, "label": "DAPI", "active": True},
            {"color": "44FF44", "window": {"start": 0, "end": 255}, "label": "Cytoplasm", "active": True},
            {"color": "FF4444", "window": {"start": 0, "end": 255}, "label": "Vessels", "active": True},
        ],
        "rdefs": {"model": "color"},
    }
    return grp


# A local zarr store: vizarr serves its chunks to the browser over the widget
# comm, on demand, as you pan and zoom
store = to_ome_zarr(synthetic_tissue(), f"{tempfile.mkdtemp()}/tissue.zarr")

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_action_button("zoom", "Zoom to center"),
            ui.hr(),
            ui.output_text_verbatim("camera"),
            width=260,
        ),
        ui.card(
            ui.card_header("Synthetic 3-channel tissue (local OME-Zarr over the Shiny comm)"),
            output_widget("vz"),
            full_screen=True,
        ),
    )
)


def server(input, output, session):
    @render_vizarr
    def vz():
        v = vizarr.Viewer()
        v.add_image(source=store, name="synthetic tissue")
        return v

    @reactive.effect
    @reactive.event(input.zoom)
    def _():
        if vz.widget is not None:
            vz.widget.view_state = {"target": [512, 512], "zoom": 2.2}

    @render.text
    def camera():
        if vz.widget is None:
            return "loading…"
        vs = reactive_read(vz.widget, "view_state")
        t = vs.get("target", [0, 0])
        return f"zoom: {vs.get('zoom', 0):.2f}\ntarget: ({t[0]:.0f}, {t[1]:.0f})"


app = App(app_ui, server)
