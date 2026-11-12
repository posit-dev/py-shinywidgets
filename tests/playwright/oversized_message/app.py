import os

# A tiny limit, so a big selection message trips the client-side guard (it
# is read when the session starts, so top-of-file is fine)
os.environ["SHINYWIDGETS_WS_MAX_SIZE"] = "65536"

import numpy as np
import plotly.graph_objects as go
from shiny.express import render
from shinywidgets import render_plotly

N = 300_000
rng = np.random.default_rng(0)
x, y = rng.normal(size=N), rng.normal(size=N)


@render_plotly
def plot():
    fig = go.Figure(go.Scattergl(x=x, y=y, mode="markers", marker=dict(size=2)))
    return fig.update_layout(dragmode="lasso")


@render.text
def selected():
    pts = plot.selected()
    return "None" if pts is None else str(len(pts))


@render.text
def heartbeat():
    return "alive"
