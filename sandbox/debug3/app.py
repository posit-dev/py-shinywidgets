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
        # Direct widget construction (no pylab): avoids the Container (and its
        # shared ipyvue Templates) that ipv.figure() creates as a side effect.
        # size_selected/color_selected must be set explicitly: their trait
        # defaults are 0-d numpy arrays, which don't JSON-serialize.
        fig = ipv.Figure()
        scatter = ipv.widgets.Scatter(
            x=x,
            y=y,
            z=z,
            size=3,
            marker="sphere",
            color="red",
            size_selected=3,
            color_selected="red",
        )
        fig.scatters = [scatter]
        return fig


app = App(app_ui, server)
