# Title: Point cloud explorer
# A small, adaptable starting point for exploring any 3D point cloud: orbit,
# resize points live, click a point for details, and read the camera.
# Bucket: template
# Run: uv run --with scikit-learn shiny run docs/widget-guides/k3d/gallery/template_point_cloud_explorer.py
# Data: sklearn.datasets.load_iris (swap in your own (n, 3) array + labels)
from __future__ import annotations

import k3d
import numpy as np
from shiny import reactive
from shiny.express import input, render, ui
from sklearn.datasets import load_iris
from shinywidgets import render_k3d

iris = load_iris(as_frame=True).frame
xyz = iris[["sepal length (cm)", "sepal width (cm)", "petal length (cm)"]].to_numpy(np.float32)
labels = iris["target"].map(dict(enumerate(["setosa", "versicolor", "virginica"])))
colors = np.choose(iris["target"].to_numpy(), [0xE41A1C, 0x377EB8, 0x4DAF4A]).astype(np.uint32)

clicked = reactive.value(None)

ui.page_opts(title="Point cloud explorer", fillable=True)
ui.input_slider("point_size", "Point size", min=0.05, max=0.4, value=0.15)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Drag to orbit, click a point")

        @render_k3d
        def plot():
            scene = k3d.plot(mode="callback")
            scene += k3d.points(
                xyz,
                colors=colors,
                point_size=0.15,
                shader="3d",
                click_callback=lambda info: clicked.set(info),
            )
            return scene

        @reactive.effect
        def _resize():
            plot.widget.objects[0].point_size = input.point_size()

    with ui.card():
        ui.card_header("Clicked point")

        @render.code
        def detail():
            info = clicked()
            if info is None:
                return "None (click a point)"
            i = info["index"]
            return f"{labels[i]} (#{i})\n{[round(v, 2) for v in info['position']]}"

        ui.card_header("plot.camera()")

        @render.code
        def camera_out():
            return ", ".join(f"{v:.1f}" for v in plot.camera())
