from __future__ import annotations

import holoviews as hvl
import hvplot.pandas  # noqa: F401
import numpy as np
import pandas as pd
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_holoviews

hvl.extension("bokeh")

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("hv"),
    output_widget("overlay"),
    output_widget("layout"),
    output_widget("styled"),
    output_widget("dynamic"),
    output_widget("hvplot_line"),
    output_widget("hvplot_group"),
)

df = pd.DataFrame(
    {
        "x": np.arange(10),
        "y": np.random.RandomState(42).rand(10),
        "cat": ["a", "b"] * 5,
    }
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

    # Basic holoviews element, re-rendered reactively
    @render_holoviews
    def hv():
        n = counter.get()
        return hvl.Curve([n, n + 1, n + 2])

    # Overlay of two elements
    @render_holoviews
    def overlay():
        return hvl.Curve([1, 2, 3]) * hvl.Scatter([(1, 1), (2, 2), (3, 3)])

    # Side-by-side layout
    @render_holoviews
    def layout():
        return hvl.Curve([1, 2, 3]) + hvl.Scatter([3, 2, 1])

    # Options: title, color, size
    @render_holoviews
    def styled():
        return hvl.Curve([1, 4, 9]).opts(
            title="styled curve", color="red", width=300, height=200
        )

    # DynamicMap renders its current state (streams require a live Python
    # server, which neither the panel nor bokeh coercion path provides)
    @render_holoviews
    def dynamic():
        return hvl.DynamicMap(
            lambda n: hvl.Curve([0, n, 2 * n]), kdims="n"
        ).redim.range(n=(1, 5))

    # hvPlot from pandas
    @render_holoviews
    def hvplot_line():
        return df.hvplot.line(x="x", y="y")

    # hvPlot with grouping (legend)
    @render_holoviews
    def hvplot_group():
        return df.hvplot.scatter(x="x", y="y", by="cat")


app = App(app_ui, server)
