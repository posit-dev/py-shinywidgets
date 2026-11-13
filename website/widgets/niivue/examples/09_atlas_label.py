# Pattern: crosshair click -> atlas region name (a "click -> detail card").
# `location()["values"]` has one entry per loaded volume, in load order --
# `values[1]["value"]` is the intensity of the *second* volume (the AAL
# atlas) under the crosshair, which for a label atlas is a region index.
import json
import urllib.request

from ipyniivue import NiiVue, Volume
from shiny import ui as core_ui
from shiny.express import render, ui
from shinywidgets import render_niivue

ui.page_opts(title="Atlas region lookup", fillable=True)

with urllib.request.urlopen("https://niivue.com/demos/images/aal.json") as resp:
    AAL_LABELS = json.load(resp)["labels"]


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_volumes(
        [
            Volume(url="https://niivue.com/demos/images/mni152.nii.gz"),
            Volume(
                url="https://niivue.com/demos/images/aal.nii.gz",
                colormap="actc",
                opacity=0.5,
            ),
        ]
    )
    return nv


@render.ui
def region_card():
    loc = brain.location()
    if loc.get("seeded"):
        return ui.p("Click a region to identify it.")
    region_index = round(loc["values"][1]["value"])
    region = AAL_LABELS[region_index] if region_index else "none (background)"
    mm = loc["mm"][:3]
    return core_ui.card(
        ui.h5(region.replace("_", " ")),
        f"MNI (x, y, z): {mm[0]:.0f}, {mm[1]:.0f}, {mm[2]:.0f} mm",
    )
