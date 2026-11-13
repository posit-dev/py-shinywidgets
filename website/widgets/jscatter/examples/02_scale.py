import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny.express import render, ui
from shinywidgets import render_jscatter

N = 2_000_000
rng = np.random.default_rng(0)
centers = rng.uniform(-5, 5, size=(8, 2))
cluster = rng.integers(0, 8, N)
xy = centers[cluster] + rng.normal(scale=0.6, size=(N, 2))
points = pd.DataFrame({"x": xy[:, 0], "y": xy[:, 1], "cluster": cluster.astype(str)})

ui.page_opts(title="2,000,000 points", fillable=True)
ui.p(f"{N:,} points on the GPU. Drag to pan, scroll to zoom, or lasso a cluster.")

with ui.card(full_screen=True):

    @render_jscatter
    def plot():
        return (
            Scatter(data=points, x="x", y="y", color_by="cluster")
            .size(default=2)
            .lasso(initiator=True)
        )

    @render.text
    def n_selected():
        return f"{len(plot.selected()):,} selected"
