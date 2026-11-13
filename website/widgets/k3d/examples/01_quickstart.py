# Needs scikit-learn for the iris dataset:
#   uv run --with scikit-learn shiny run docs/widget-guides/k3d/examples/01_quickstart.py
from __future__ import annotations

import k3d
import numpy as np
from shiny.express import ui
from sklearn.datasets import load_iris
from shinywidgets import render_k3d

iris = load_iris(as_frame=True).frame
xyz = iris[["sepal length (cm)", "sepal width (cm)", "petal length (cm)"]].to_numpy(np.float32)
species_color = np.choose(iris["target"].to_numpy(), [0xE41A1C, 0x377EB8, 0x4DAF4A]).astype(np.uint32)

ui.page_opts(title="Iris in 3D", fillable=True)


@render_k3d
def plot():
    scene = k3d.plot()
    scene += k3d.points(xyz, colors=species_color, point_size=0.2, shader="3d")
    return scene
