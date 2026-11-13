# `location()` debounces at 250ms by default (a crosshair drag reports ~20
# times a second). Pass `rate_delay=0` to react to every event instead --
# useful when you want each click to register immediately and aren't
# dragging continuously.
from ipyniivue import NiiVue, Volume
from shiny.express import render, ui
from shinywidgets import render_niivue

ui.page_opts(title="No debounce", fillable=True)


@render_niivue(rate_delay=0)
def brain():
    nv = NiiVue()
    nv.load_volumes([Volume(url="https://niivue.com/demos/images/mni152.nii.gz")])
    return nv


@render.code
def readout():
    loc = brain.location()
    return "Click the brain to inspect a voxel" if loc.get("seeded") else loc["string"]
