from __future__ import annotations

from ipyniivue import NiiVue, Volume
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_niivue

app_ui = ui.page_fluid(
    ui.input_action_button("burst", "Burst"),
    output_widget("brain", height="400px"),
    ui.output_text("loaded"),
    ui.output_text("location"),
    ui.output_text("publish_count"),
)

# Number of synthetic crosshair events the Burst button drives
BURST_N = 20


def server(input, output, session):
    image_loaded = reactive.value(False)
    n_publishes = reactive.value(0)

    @render_niivue
    def brain():
        nv = NiiVue()
        nv.load_volumes([Volume(url="https://niivue.com/demos/images/mni152.nii.gz")])

        @nv.on_image_loaded
        def _(_volume):
            image_loaded.set(True)

        return nv

    # Count PUBLISHES of the location accessor (one reactive.Value.set per
    # publish). Unlike an evaluation count, this is insensitive to reactive
    # flush batching: without the debounce, the burst publishes 20 times (20
    # distinct set() calls, however they batch into flushes); with it, once
    loc_value = brain._accessors.values["location"]
    original_set = loc_value.set

    def counting_set(box):
        # Value.get() outside a reactive context raises; and exceptions in
        # ipywidgets message handlers are swallowed silently
        with reactive.isolate():
            n_publishes.set(n_publishes.get() + 1)
        return original_set(box)

    loc_value.set = counting_set

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

    @render.text
    def loaded():
        return "yes" if image_loaded() else "no"

    @render.text
    def location():
        value = brain.location()
        if value is None:
            return "None"
        return ",".join(f"{v:.1f}" for v in value["mm"])

    @render.text
    def publish_count():
        return str(n_publishes())


app = App(app_ui, server)
