# Driving a DynamicMap with a stream updates the existing plot: the bokeh
# model stays put, so pan/zoom state survives. Re-rendering (left as a
# contrast on the right) builds a brand-new plot every time, which resets
# the view. Click "New data" after zooming into both to see the difference.
import holoviews as hv
import numpy as np
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

rng = np.random.default_rng(0)


def random_walk(n=200):
    return np.cumsum(rng.normal(size=n))


ui.page_opts(title="In-place update vs. re-render", fillable=True)
ui.input_action_button("refresh", "New data")

pipe = hv.streams.Pipe(data=random_walk())

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("In place: hv.streams.Pipe (preserves zoom)")

        @render_holoviews
        def in_place():
            return hv.DynamicMap(
                lambda data: hv.Curve(data).opts(responsive=True), streams=[pipe]
            )

    with ui.card(full_screen=True):
        ui.card_header("Re-render: reads a reactive value directly (resets zoom)")
        data = reactive.value(random_walk())

        @render_holoviews
        def rerendered():
            return hv.Curve(data()).opts(responsive=True)


@reactive.effect
@reactive.event(input.refresh)
def _():
    new_data = random_walk()
    pipe.send(new_data)
    data.set(new_data)
