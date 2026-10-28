from __future__ import annotations

import ipyvolume as ipv
import numpy as np
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipyvolume

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("plot", height="400px"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_ipyvolume
    def plot():
        counter.get()
        rng = np.random.default_rng(0)
        x, y, z = rng.random((3, 500))
        # The pylab API also constructs a (never rendered) Container whose
        # ipyvue Template children are process-wide singletons, so this
        # exercises them surviving each re-render's cleanup
        ipv.quickscatter(x, y, z, size=1, marker="sphere", color="red")
        return ipv.gcf()


app = App(app_ui, server)
