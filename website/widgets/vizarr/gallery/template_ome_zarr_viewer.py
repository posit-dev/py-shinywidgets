# vizarr OME-Zarr viewer template
# A clean starting point for browsing a public OME-NGFF/OME-Zarr dataset: a
# full-screen viewer, a "reset view" button, and a live camera readout driven
# by viewer.read("view_state"). Swap IDR_SAMPLE for your own store's URL (or
# a local zarr.Group/Array/numpy array -- see docs/widget-guides/vizarr/guide.md).
# bucket: template
# run: uv run --with 'shinywidgets[vizarr]' shiny run template_ome_zarr_viewer.py
# data: Image Data Resource (IDR), dataset idr0062-blin-nuclearsegmentation,
#       https://idr.openmicroscopy.org (public, no key required)
import vizarr
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_vizarr

IDR_SAMPLE = "https://minio-dev.openmicroscopy.org/idr/v0.3/idr0062-blin-nuclearsegmentation/6001240.zarr"
HOME_VIEW = {"target": [256, 256], "zoom": -0.6}

ui.page_opts(title="OME-Zarr viewer", fillable=True)

with ui.layout_sidebar():
    with ui.sidebar(width=260):
        ui.input_action_button("reset_view", "Reset view")
        ui.hr()

        @render.code
        def camera_readout():
            vs = viewer.read("view_state")
            if not vs:
                return "loading..."
            target = vs.get("target", [0, 0])
            return f"zoom:   {vs.get('zoom', 0):.2f}\ntarget: ({target[0]:.0f}, {target[1]:.0f})"

    with ui.card(full_screen=True):
        ui.card_header("Image")

        @render_vizarr
        def viewer():
            v = vizarr.Viewer()
            v.add_image(source=IDR_SAMPLE)
            return v


@reactive.effect
@reactive.event(input.reset_view)
def _():
    if viewer.widget is not None:
        viewer.widget.view_state = HOME_VIEW
