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
        # Direct widget construction instead of the pylab API: ipv.figure()
        # also constructs a Container whose (shared, cached) ipyvue Template
        # children get closed by the first re-render's cleanup, which leaves
        # the browser waiting on models that never re-open. See
        # https://github.com/posit-dev/py-shinywidgets/issues/278
        # size_selected/color_selected must be set explicitly: their trait
        # defaults are 0-d numpy arrays, which don't JSON-serialize.
        fig = ipv.Figure()
        scatter = ipv.widgets.Scatter(
            x=x,
            y=y,
            z=z,
            size=1,
            marker="sphere",
            color="red",
            size_selected=1,
            color_selected="red",
        )
        fig.scatters = [scatter]
        return fig


app = App(app_ui, server)
