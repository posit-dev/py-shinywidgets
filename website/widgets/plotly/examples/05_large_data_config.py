import numpy as np
import plotly.graph_objects as go
from shiny.express import ui
from shinywidgets import render_plotly

rng = np.random.default_rng(0)
n = 200_000
x = rng.normal(size=n)
y = x * 0.6 + rng.normal(size=n)

ui.page_opts(title="200k points", fillable=True)


@render_plotly
def big_scatter():
    fig = go.Figure(
        go.Scattergl(x=x, y=y, mode="markers", marker=dict(size=3, opacity=0.3))
    )
    return fig, {"displayModeBar": False}
