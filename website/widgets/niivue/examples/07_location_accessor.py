# `brain.location()` reads the crosshair position reactively, like a Shiny
# input. It's seeded at render with the volume's center (`seeded: True`,
# no `mm`/`values` yet), and updates (debounced) as the user moves the
# crosshair.
from ipyniivue import NiiVue, Volume
from shiny.express import render, ui
from shinywidgets import render_niivue

ui.page_opts(title="Crosshair location", fillable=True)


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_volumes([Volume(url="https://niivue.com/demos/images/mni152.nii.gz")])
    return nv


@render.code
def readout():
    loc = brain.location()
    if loc.get("seeded"):
        return "Click the brain to inspect a voxel"
    mm = loc["mm"][:3]
    value = loc["values"][0]["value"]
    return f"mm: ({mm[0]:.1f}, {mm[1]:.1f}, {mm[2]:.1f})\nintensity: {value:.1f}"
