"""Brain imaging in Shiny: a NiiVue (ipyniivue) multiplanar + 3D viewer.

The first run downloads the public NiiVue demo images (mni152 structural scan +
hippocampus overlay, ~4.5 MB) into a cache dir; subsequent runs reuse them.
"""

from pathlib import Path

from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_niivue

from ipyniivue import NiiVue, SliceType, Volume, download_dataset

DATA = Path.home() / ".cache" / "ipyniivue-demo"
if not (DATA / "mni152.nii.gz").exists():
    download_dataset(dest_folder=DATA, files=["mni152.nii.gz", "hippo.nii.gz"])

SLICES = {"Multiplanar": SliceType.MULTIPLANAR, "3D render": SliceType.RENDER}
CMAPS = ["gray", "viridis", "hot", "winter", "copper"]

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("cmap", "Background colormap", CMAPS),
            ui.input_slider("gamma", "Gamma", 0.2, 2.5, 1.0, step=0.05),
            ui.input_slider("opacity", "Overlay opacity", 0.0, 1.0, 0.6, step=0.05),
            ui.input_radio_buttons("slicetype", "View", list(SLICES)),
            width=270,
        ),
        ui.card(
            ui.card_header(
                "MNI152 brain + hippocampus overlay — click/drag to move the crosshair"
            ),
            ui.output_text("crosshair"),
            output_widget("nv"),
            full_screen=True,
        ),
    ),
)


def server(input, output, session):
    # Session-scoped: browser -> Python crosshair events land here.
    location = reactive.Value("crosshair: —")

    @render_niivue
    def nv():
        w = NiiVue()
        w.load_volumes(
            [
                Volume(path=str(DATA / "mni152.nii.gz"), name="mni152", colormap="gray"),
                Volume(
                    path=str(DATA / "hippo.nii.gz"),
                    name="hippocampus",
                    colormap="red",
                    opacity=0.6,
                ),
            ]
        )

        @w.on_location_change
        def _(loc):
            # NOTE: loc["values"] is a list of dicts (one per volume), not floats;
            # loc["string"] is the frontend's pre-formatted mm + intensity readout.
            mm = [round(v, 1) for v in loc["mm"][:3]]
            location.set(f"crosshair (mm): {mm}   |   {loc['string']}")

        return w

    @render.text
    def crosshair():
        return location()

    @reactive.effect
    @reactive.event(input.cmap)
    def _():
        nv.widget.set_colormap(nv.widget.volumes[0].id, input.cmap())

    @reactive.effect
    @reactive.event(input.gamma)
    def _():
        nv.widget.set_gamma(input.gamma())

    @reactive.effect
    @reactive.event(input.opacity)
    def _():
        nv.widget.set_opacity(1, input.opacity())

    @reactive.effect
    @reactive.event(input.slicetype)
    def _():
        nv.widget.set_slice_type(SLICES[input.slicetype()])


app = App(app_ui, server)
