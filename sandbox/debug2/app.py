from __future__ import annotations

import ipyvolume as ipv
import numpy as np
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipyvolume

# Kept to a single figure on purpose: each ipyvolume figure initializes its
# own WebGL context synchronously on the page's main thread, so the
# multi-figure page (tests/playwright/render_ipyvolume) is a poor place to
# test re-render interactions (clicks land while the main thread is stalled)
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
        ipv.figure()
        ipv.scatter(x, y, z, size=1, marker="sphere", color="red")
        fig = ipv.gcf()

        import logging

        from shinywidgets._widget_registry import WIDGET_INSTANCE_MAP

        for wid, w in WIDGET_INSTANCE_MAP.items():
            logging.warning(f"WIDGET {wid} {type(w).__module__}.{type(w).__name__}")
        return fig


app = App(app_ui, server)
