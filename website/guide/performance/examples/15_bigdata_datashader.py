import os

import holoviews as hv
import numpy as np
import pandas as pd
from holoviews.operation.datashader import rasterize
from shiny.express import ui
from shinywidgets import render_holoviews

hv.extension("bokeh")

N = int(os.environ.get("PERF_N", "10000"))
rng = np.random.default_rng(42)
df = pd.DataFrame({"x": rng.normal(size=N), "y": rng.normal(size=N)})

ui.page_opts(title=f"datashader rasterize: {N:,} points", fillable=True)


@render_holoviews
def plot():
    # A fixed pixel size (not responsive=True) isolates the payload's
    # dependence on N from its dependence on viewport/DPI -- the point of
    # this example is that the former is flat, which a responsive size
    # would otherwise confound.
    points = hv.Points(df, ["x", "y"])
    return rasterize(points, width=700, height=450).opts(
        width=700, height=450, cmap="fire", cnorm="eq_hist", colorbar=True
    )
