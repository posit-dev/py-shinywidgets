# Switch between 2D slice views and the 3D volume render without re-sending
# the (multi-megabyte) volume -- `set_slice_type` applies in place.
from ipyniivue import NiiVue, SliceType, Volume
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_niivue

SLICES = {
    "Axial": SliceType.AXIAL,
    "Coronal": SliceType.CORONAL,
    "Sagittal": SliceType.SAGITTAL,
    "Multiplanar": SliceType.MULTIPLANAR,
    "3D render": SliceType.RENDER,
}

ui.page_opts(title="Slice types", fillable=True)
ui.input_radio_buttons("view", "View", list(SLICES), selected="Multiplanar", inline=True)


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_volumes([Volume(url="https://niivue.com/demos/images/mni152.nii.gz")])
    return nv


@reactive.effect
def _():
    brain.widget.set_slice_type(SLICES[input.view()])
