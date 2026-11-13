import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(2)
n = 600
label = rng.integers(0, 5, n)
grid_x, grid_y = (np.arange(n) % 30).astype(float), (np.arange(n) // 30).astype(float)
angle = rng.uniform(0, 2 * np.pi, n)
radius = label + rng.normal(0, 0.15, n)
points = pd.DataFrame(
    {
        "grid_x": grid_x,
        "grid_y": grid_y,
        "circle_x": radius * np.cos(angle),
        "circle_y": radius * np.sin(angle),
        "label": label.astype(str),
    }
)

ui.page_opts(title="Animated transition between embeddings", fillable=True)
ui.input_action_button("toggle", "Switch embedding", class_="mb-2")

with ui.card(full_screen=True):

    @render_jscatter
    def plot():
        return Scatter(data=points, x="grid_x", y="grid_y", color_by="label")

    @reactive.effect
    @reactive.event(input.toggle)
    def _switch():
        to_circle = input.toggle() % 2 == 1
        x, y = ("circle_x", "circle_y") if to_circle else ("grid_x", "grid_y")
        with reactive.isolate():
            plot.value.xy(x=x, y=y, animate=True)
