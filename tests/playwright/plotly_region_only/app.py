import numpy as np
import plotly.graph_objects as go
from shiny.express import render, ui
from shinywidgets import render_plotly

# The #459 repro: a big point cloud, and only the selection *region* read.
# With no listen_to, shinywidgets' bridge is never asked for per-point
# selection payloads, so none of its messages grow with the selection.
# (plotly.py's own FigureWidget channel still reports selections over its
# `_js2py_pointsCallback` trait -- shinywidgets can't gate that; the
# client-side size guard is the backstop there.)
N = 300_000
rng = np.random.default_rng(0)
x, y = rng.normal(size=N), rng.normal(size=N)

ui.p("No listen_to: only brushed() is read")


@render_plotly
def plot():
    fig = go.Figure(go.Scattergl(x=x, y=y, mode="markers", marker=dict(size=2)))
    return fig.update_layout(dragmode="lasso")


@render.text
def brushed():
    return str(plot.brushed())
