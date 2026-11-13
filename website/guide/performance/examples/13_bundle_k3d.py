import k3d
import numpy as np
from shiny.express import ui
from shinywidgets import render_k3d

ui.page_opts(title="bundle: k3d", fillable=True)


@render_k3d
def plot():
    scene = k3d.plot()
    scene += k3d.points(np.random.default_rng(42).normal(size=(50, 3)).astype("float32"))
    return scene
