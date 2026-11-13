# Title: Brain atlas explorer
# A fuller NiiVue app: jump the crosshair to a named landmark from Python,
# click to look up the AAL region and MNI coordinate under the crosshair,
# and adjust the atlas overlay's colormap/opacity in place -- all without
# re-rendering the viewer.
# Bucket: showcase
# Run: uv run --with nibabel shiny run app.py
# Data: MNI152 template + AAL atlas volumes (niivue.com demo images, fetched
#   by the browser) and the AAL region-label JSON (fetched once at startup);
#   the landmark jump needs the MNI152 file locally too, so it's cached with
#   `download_dataset()` on first run.
import json
import urllib.request
from pathlib import Path

import nibabel as nib
import numpy as np
from ipyniivue import NiiVue, SliceType, Volume, download_dataset
from shiny import reactive
from shiny import ui as core_ui
from shiny.express import input, render, ui
from shinywidgets import render_niivue

LANDMARKS_MM = {
    "Left amygdala": (-23, -5, -18),
    "Right amygdala": (23, -5, -18),
    "Anterior cingulate": (0, 30, 20),
    "Left motor cortex (hand knob)": (-38, -22, 52),
    "Primary visual cortex": (10, -88, 4),
}
CMAPS = ["actc", "warm", "redyell", "winter", "jet"]

with urllib.request.urlopen("https://niivue.com/demos/images/aal.json") as resp:
    AAL_LABELS = json.load(resp)["labels"]

CACHE = Path.home() / ".cache" / "niivue-guide"
if not (CACHE / "mni152.nii.gz").exists():
    download_dataset(dest_folder=CACHE, files=["mni152.nii.gz"])
MNI = nib.load(CACHE / "mni152.nii.gz")
TO_VOX = np.linalg.inv(MNI.affine)

ui.page_opts(title="Brain atlas explorer", fillable=True)

with ui.sidebar(width=300):
    ui.input_select("landmark", "Jump to", list(LANDMARKS_MM))
    ui.input_radio_buttons(
        "view",
        "View",
        {"multiplanar": "Multiplanar", "render": "3D render"},
        inline=True,
    )
    ui.input_select("cmap", "Atlas colormap", CMAPS)
    ui.input_slider("opacity", "Atlas opacity", 0.0, 1.0, value=0.5, step=0.05)
    ui.markdown("---")

    @render.ui
    def region_card():
        loc = brain.location()
        # location() seeds at render from the viewer's current crosshair, so
        # it's never None; a seeded payload only carries "frac", not the
        # "values"/"mm" a real click or crosshair report fills in -- check
        # "seeded" instead of `is None`.
        if loc.get("seeded"):
            return ui.p("Click the brain, or jump to a landmark, to identify it.")
        region_index = round(loc["values"][1]["value"])
        region = AAL_LABELS[region_index] if region_index else "none (background)"
        mm = loc["mm"][:3]
        return core_ui.card(
            core_ui.h5(region.replace("_", " ")),
            f"MNI (x, y, z): {mm[0]:.0f}, {mm[1]:.0f}, {mm[2]:.0f} mm",
        )


with ui.card(full_screen=True):

    @render_niivue
    def brain():
        nv = NiiVue()
        nv.load_volumes(
            [
                Volume(path=CACHE / "mni152.nii.gz"),
                Volume(
                    url="https://niivue.com/demos/images/aal.nii.gz",
                    colormap="actc",
                    opacity=0.5,
                ),
            ]
        )
        return nv


@reactive.effect
def _():
    mm = LANDMARKS_MM[input.landmark()]
    vox = (TO_VOX @ np.array([*mm, 1.0]))[:3]
    brain.widget.scene.crosshair_pos = list(vox / np.array(MNI.shape))


@reactive.effect
def _():
    slice_type = SliceType.RENDER if input.view() == "render" else SliceType.MULTIPLANAR
    brain.widget.set_slice_type(slice_type)


@reactive.effect
def _():
    atlas = brain.widget.volumes[1]
    brain.widget.set_colormap(atlas.id, input.cmap())
    brain.widget.set_opacity(1, input.opacity())
