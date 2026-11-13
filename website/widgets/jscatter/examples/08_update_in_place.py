import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(1)
n = 3000
origin = pd.Series(rng.choice(["USA", "Europe", "Japan"], n, p=[0.5, 0.25, 0.25]))
weight = origin.map({"USA": 3.4, "Europe": 2.6, "Japan": 2.4}) + rng.normal(0, 0.5, n)
cars = pd.DataFrame({"origin": origin.astype("category"), "weight": weight.round(2)})
cars["mpg"] = (45 - 6 * cars["weight"] + rng.normal(0, 2.5, n)).round(1)

ui.page_opts(title="Restyle in place, without re-sending data", fillable=True)
ui.input_action_button("toggle", "Color by weight instead", class_="mb-2")

with ui.card(full_screen=True):

    @render_jscatter
    def plot():
        return Scatter(data=cars, x="weight", y="mpg", color_by="origin")

    @reactive.effect
    @reactive.event(input.toggle)
    def _recolor():
        by_weight = input.toggle() % 2 == 1
        with reactive.isolate():
            if by_weight:
                plot.value.color(by="weight", map="viridis")
            else:
                plot.value.color(by="origin")
