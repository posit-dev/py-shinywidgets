from __future__ import annotations

from ipyniivue import NiiVue, Volume
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_niivue

app_ui = ui.page_fluid(
    ui.input_action_button("burst", "Burst"),
    output_widget("brain", height="400px"),
    ui.output_text("loaded"),
    ui.output_text("location"),
    ui.output_text("eval_count"),
)

# Number of synthetic crosshair events the Burst button drives
BURST_N = 20


def server(input, output, session):
    n_evals = [0]
    image_loaded = reactive.value(False)

    @render_niivue
    def brain():
        nv = NiiVue()
        nv.load_volumes([Volume(url="https://niivue.com/demos/images/mni152.nii.gz")])

        @nv.on_image_loaded
        def _(_volume):
            image_loaded.set(True)

        return nv

    # Drive BURST_N synthetic crosshair events in a tight loop (the same drive
    # mechanism as the unit tests): all of them must coalesce into a single
    # debounced publish
    @reactive.effect
    @reactive.event(input.burst)
    def _():
        for i in range(BURST_N):
            brain.widget._handle_custom_msg(
                {
                    "event": "location_change",
                    "data": {
                        "ax_cor_sag": 0,
                        "frac": [0.5, 0.5, 0.5],
                        "mm": [float(i), 0.0, 0.0],
                        "vox": [i, 0, 0],
                        "values": [0.0],
                        "string": "burst",
                        "xy": [0, 0],
                    },
                },
                None,
            )

    @reactive.calc
    def loc():
        n_evals[0] += 1
        return brain.location()

    @render.text
    def loaded():
        return "yes" if image_loaded() else "no"

    @render.text
    def location():
        value = loc()
        if value is None:
            return "None"
        return ",".join(f"{v:.1f}" for v in value["mm"])

    @render.text
    def eval_count():
        loc()
        return str(n_evals[0])


app = App(app_ui, server)
