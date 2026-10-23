from __future__ import annotations

import holoviews as hv
import hvplot.pandas  # noqa: F401
import numpy as np
import pandas as pd
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_holoviews

hv.extension("bokeh")

rng = np.random.default_rng(0)
n = 200_000
df = pd.DataFrame({"x": rng.normal(size=n), "y": rng.normal(size=n)})

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("aggregations"),
    output_widget("points"),
)


def server(input, output, session):
    counter = reactive.value(0)
    # x-ranges of every image datashader produced, appended by the server
    # whenever it (re-)aggregates
    x_ranges: reactive.Value[list[tuple[float, float]]] = reactive.value([])

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render.text
    def aggregations():
        return " ".join(f"{lo:.3f},{hi:.3f}" for lo, hi in x_ranges.get())

    def record(img: hv.Image) -> hv.Image:
        lo, hi = img.range("x")
        # Also runs inside the render function (initial aggregation), which
        # mustn't take a dependency on x_ranges
        with reactive.isolate():
            x_ranges.set([*x_ranges.get(), (float(lo), float(hi))])
        return img

    @render_holoviews
    def points():
        counter.get()
        x_ranges.set([])
        return df.hvplot.points("x", "y", rasterize=True).apply(record)


app = App(app_ui, server)
