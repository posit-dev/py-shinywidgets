# Repro: a hv.streams.RangeXY subscriber inside @render_holoviews causes an
# infinite re-render loop (BokehModel was closed... errors spamming the log),
# even with zero user interaction -- just loading the page is enough.
import holoviews as hv
import hvplot.pandas  # noqa: F401
import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_holoviews

hv.extension("bokeh")
ui.page_opts(fillable=True)

rng = np.random.default_rng(0)
df = pd.DataFrame({"x": rng.normal(size=300), "y": rng.normal(size=300)})

range_count = reactive.value(0)


@render_holoviews
def plot():
    scatter = df.hvplot.scatter("x", "y", responsive=True)
    rxy = hv.streams.RangeXY(source=scatter)

    def on_range(x_range, y_range):
        range_count.set(range_count.get() + 1)

    rxy.add_subscriber(on_range)
    return scatter


@render.code
def counts():
    return f"range_count={range_count()}"
