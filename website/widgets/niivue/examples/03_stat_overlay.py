# A thresholded statistical-map overlay (an unthresholded NARPS group z-map)
# on the MNI152 template, with colormap/threshold/opacity driven by inputs.
from ipyniivue import NiiVue, Volume
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_niivue

ui.page_opts(title="Statistical overlay", fillable=True)
with ui.sidebar():
    ui.input_select("cmap", "Colormap", ["warm", "redyell", "winter", "actc"])
    ui.input_slider("thresh", "Threshold |z|", 0.0, 6.0, value=2.3, step=0.1)
    ui.input_slider("opacity", "Opacity", 0.0, 1.0, value=0.8, step=0.05)


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_volumes(
        [
            Volume(url="https://niivue.com/demos/images/mni152.nii.gz"),
            Volume(
                url="https://niivue.com/demos/images/narps-4735_50GV-hypo1_unthresh.nii.gz",
                colormap="warm",
                cal_min=2.3,
                cal_max=6.0,
                opacity=0.8,
            ),
        ]
    )
    return nv


@reactive.effect
def _():
    overlay = brain.widget.volumes[1]
    brain.widget.set_colormap(overlay.id, input.cmap())
    overlay.cal_min = input.thresh()
    brain.widget.set_opacity(1, input.opacity())
