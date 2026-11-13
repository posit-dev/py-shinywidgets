# 4D volumes (here, a perfusion MRI time series) carry a `frame_4d` trait --
# scrub through frames in place, no re-render.
from ipyniivue import NiiVue, Volume
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_niivue

ui.page_opts(title="4D volume frames", fillable=True)
ui.input_slider("frame", "Frame", 0, 9, value=0)


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_volumes([Volume(url="https://niivue.com/demos/images/pcasl.nii.gz")])
    return nv


@reactive.effect
def _():
    brain.widget.volumes[0].frame_4d = input.frame()
