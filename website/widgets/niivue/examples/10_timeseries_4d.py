# Pattern: crosshair click -> time series plot. NiiVue reports the voxel
# under the crosshair (`location()["vox"]`), but only its intensity in the
# *currently displayed* frame -- for the full time course, index into the
# same 4D array locally with nibabel. (First run downloads the ~0.6 MB demo
# scan into a cache folder.)
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
from ipyniivue import NiiVue, Volume, download_dataset
from shiny.express import render, ui
from shinywidgets import render_niivue

ui.page_opts(title="4D intensity profile", fillable=True)

CACHE = Path.home() / ".cache" / "niivue-guide"
if not (CACHE / "pcasl.nii.gz").exists():
    download_dataset(dest_folder=CACHE, files=["pcasl.nii.gz"])
TIMESERIES = nib.load(CACHE / "pcasl.nii.gz").get_fdata()  # shape: (x, y, z, time)


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_volumes([Volume(path=CACHE / "pcasl.nii.gz")])
    return nv


@render.plot
def profile():
    loc = brain.location()
    fig, ax = plt.subplots()
    if loc.get("seeded"):
        ax.set_title("Click the scan to plot a voxel's time course")
        return fig
    i, j, k = loc["vox"]
    ax.plot(TIMESERIES[i, j, k, :], marker="o")
    ax.set(xlabel="frame", ylabel="signal", title=f"Voxel {(i, j, k)}")
    return fig
