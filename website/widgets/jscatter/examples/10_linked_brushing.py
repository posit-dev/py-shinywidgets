import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(1)
n = 3000
origin = pd.Series(rng.choice(["USA", "Europe", "Japan"], n, p=[0.5, 0.25, 0.25]))
weight = origin.map({"USA": 3.4, "Europe": 2.6, "Japan": 2.4}) + rng.normal(0, 0.5, n)
cars = pd.DataFrame({"origin": origin.astype("category"), "weight": weight.round(2)})
cars["mpg"] = (45 - 6 * cars["weight"] + rng.normal(0, 2.5, n)).round(1)
cars["hp"] = (45 * cars["weight"] + rng.normal(0, 25, n)).round()

ui.page_opts(title="Linked brushing between two jscatter plots", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Weight vs. MPG")

        @render_jscatter
        def weight_mpg():
            return Scatter(data=cars, x="weight", y="mpg", color_by="origin").lasso(
                initiator=True
            )

    with ui.card(full_screen=True):
        ui.card_header("Horsepower vs. MPG")

        @render_jscatter
        def hp_mpg():
            return Scatter(data=cars, x="hp", y="mpg", color_by="origin").lasso(
                initiator=True
            )


def link(source, target):
    @reactive.effect
    def _():
        selection = source.selected()
        with reactive.isolate():
            if not np.array_equal(selection, target.widget.selection):
                target.widget.selection = selection


link(weight_mpg, hp_mpg)
link(hp_mpg, weight_mpg)
