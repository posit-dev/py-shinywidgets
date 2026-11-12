from __future__ import annotations

from ipyniivue import NiiVue, Volume
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_niivue

# The accessor reads the tests assert on are gated behind an action button,
# and NOTHING reads the accessor at startup, so the drag below lands before
# the accessor's first read. The accessor attaches at render: the drag's
# stream updates must be reflected in the gated first read, and the
# frontend's 30 ms scene poll must sync the drag to the Python-side trait the
# seed reads from (see the tests).

app_ui = ui.page_fluid(
    ui.input_action_button("read_location", "Read location"),
    output_widget("brain", height="400px"),
    ui.output_text("loaded"),
    ui.output_text("location"),
    ui.output_text("trait"),
)


def server(input, output, session):
    image_loaded = reactive.value(False)

    @render_niivue
    def brain():
        nv = NiiVue()
        nv.load_volumes([Volume(url="https://niivue.com/demos/images/mni152.nii.gz")])

        @nv.on_image_loaded
        def _(_volume):
            image_loaded.set(True)

        return nv

    @render.text
    def loaded():
        return "yes" if image_loaded() else "no"

    @render.text
    @reactive.event(input.read_location)
    def location():
        value = brain.location()
        if value is None:
            return "None"
        # A seeded value carries only frac (plus the marker); a streamed one
        # carries the full payload
        if value.get("seeded"):
            return "seed:" + ",".join(f"{v:.3f}" for v in value["frac"])
        return "stream:" + ",".join(f"{v:.1f}" for v in value["mm"])

    @render.text
    @reactive.event(input.read_location)
    def trait():
        # The Python-side scene trait the frontend's scene poll syncs to --
        # where location()'s attach-time seed reads from
        return ",".join(f"{v:.3f}" for v in brain.widget.scene.crosshair_pos)


app = App(app_ui, server)
