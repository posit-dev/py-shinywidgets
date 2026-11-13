# Pattern: a Shiny input jumps the crosshair (no re-render). `location()`
# only reports *browser*-originated moves, and `nv.frac2mm()` doesn't work
# server-side (the coordinate matrices live only in the browser) -- so
# converting a known MNI millimeter coordinate takes the affine from the
# same file loaded locally with nibabel. Setting `scene.crosshair_pos`
# (fractional x, y, z) moves the crosshair in place.
from pathlib import Path

import nibabel as nib
import numpy as np
from ipyniivue import NiiVue, Volume, download_dataset
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_niivue

ui.page_opts(title="Jump to a landmark", fillable=True)

LANDMARKS_MM = {
    "Left amygdala": (-23, -5, -18),
    "Right amygdala": (23, -5, -18),
    "Anterior cingulate": (0, 30, 20),
    "Left motor cortex (hand knob)": (-38, -22, 52),
}
ui.input_select("landmark", "Jump to", list(LANDMARKS_MM))

CACHE = Path.home() / ".cache" / "niivue-guide"
if not (CACHE / "mni152.nii.gz").exists():
    download_dataset(dest_folder=CACHE, files=["mni152.nii.gz"])
MNI = nib.load(CACHE / "mni152.nii.gz")
TO_VOX = np.linalg.inv(MNI.affine)


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_volumes([Volume(path=CACHE / "mni152.nii.gz")])
    return nv


@reactive.effect
def _():
    mm = LANDMARKS_MM[input.landmark()]
    vox = (TO_VOX @ np.array([*mm, 1.0]))[:3]
    brain.widget.scene.crosshair_pos = list(vox / np.array(MNI.shape))
