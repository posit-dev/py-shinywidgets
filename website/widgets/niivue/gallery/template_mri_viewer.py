# Title: Minimal MRI viewer
# A clean starting point for a NiiVue viewer: slice-type / colormap / gamma
# controls that update the volume in place, plus a crosshair readout driven
# by the `location()` accessor.
# Bucket: template
# Run: uv run --with ipyniivue shiny run docs/widget-guides/niivue/gallery/template_mri_viewer.py
# Data: MNI152 template volume, fetched by the browser from niivue.com

from ipyniivue import NiiVue, SliceType, Volume
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_niivue

SLICES = {
    "Multiplanar": SliceType.MULTIPLANAR,
    "Axial": SliceType.AXIAL,
    "Coronal": SliceType.CORONAL,
    "Sagittal": SliceType.SAGITTAL,
    "3D render": SliceType.RENDER,
}
CMAPS = ["gray", "viridis", "hot", "winter", "copper", "bone"]

ui.page_opts(title="MRI viewer", fillable=True)

with ui.sidebar():
    ui.input_radio_buttons("view", "View", list(SLICES), selected="Multiplanar")
    ui.input_select("cmap", "Colormap", CMAPS)
    ui.input_slider("gamma", "Gamma", 0.2, 2.5, value=1.0, step=0.05)
    ui.markdown("**Crosshair**")

    @render.code
    def readout():
        loc = brain.location()
        return "Click the brain" if loc.get("seeded") else loc["string"].strip()


with ui.card(full_screen=True):

    @render_niivue
    def brain():
        nv = NiiVue()
        nv.load_volumes([Volume(url="https://niivue.com/demos/images/mni152.nii.gz")])
        return nv


@reactive.effect
def _():
    brain.widget.set_slice_type(SLICES[input.view()])


@reactive.effect
def _():
    brain.widget.set_colormap(brain.widget.volumes[0].id, input.cmap())


@reactive.effect
def _():
    brain.widget.set_gamma(input.gamma())
