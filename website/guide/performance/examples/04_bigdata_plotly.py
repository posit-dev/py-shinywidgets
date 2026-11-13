import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from shiny.express import ui
from shinywidgets import render_plotly

N = int(os.environ.get("PERF_N", "10000"))
rng = np.random.default_rng(42)
df = pd.DataFrame({"x": rng.normal(size=N), "y": rng.normal(size=N)})

ui.page_opts(title=f"plotly scattergl: {N:,} points", fillable=True)


@render_plotly
def plot():
    return go.FigureWidget(
        data=[go.Scattergl(x=df["x"], y=df["y"], mode="markers", marker=dict(size=3))]
    )
