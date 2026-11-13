# Needs scikit-learn for the iris dataset:
#   uv run --with scikit-learn shiny run docs/widget-guides/k3d/examples/12_fly_to.py
from __future__ import annotations

import k3d
import numpy as np
from shiny import reactive
from shiny.express import input, ui
from sklearn.datasets import load_iris
from shinywidgets import render_k3d

iris = load_iris(as_frame=True).frame
xyz = iris[["sepal length (cm)", "sepal width (cm)", "petal length (cm)"]].to_numpy(np.float32)
species_color = np.choose(iris["target"].to_numpy(), [0xE41A1C, 0x377EB8, 0x4DAF4A]).astype(np.uint32)
species_names = ["setosa", "versicolor", "virginica"]
centroids = {name: xyz[iris["target"] == i].mean(axis=0) for i, name in enumerate(species_names)}
HOME = [10, -6, 6, 5.8, 3.0, 3.8, 0, 0, 1]

ui.page_opts(title="Fly to a species", fillable=True)
with ui.layout_columns():
    ui.input_action_button("home", "Home")
    for name in species_names:
        ui.input_action_button(name, name.title())


with ui.card(full_screen=True):

    @render_k3d
    def scene():
        plot = k3d.plot(camera_auto_fit=False)
        plot.camera = HOME
        plot += k3d.points(xyz, colors=species_color, point_size=0.15, shader="3d")
        return plot


@reactive.effect
@reactive.event(input.home)
def _fly_home():
    scene.widget.camera = HOME


def make_fly_to(name: str):
    @reactive.effect
    @reactive.event(getattr(input, name))
    def _fly():
        cx, cy, cz = (float(v) for v in centroids[name])
        scene.widget.camera = [cx + 2, cy - 2, cz + 2, cx, cy, cz, 0, 0, 1]

    return _fly


_fly_effects = [make_fly_to(name) for name in species_names]
