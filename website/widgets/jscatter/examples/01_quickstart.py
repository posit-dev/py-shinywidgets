import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny.express import render, ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(1)
n = 3000
origin = pd.Series(rng.choice(["USA", "Europe", "Japan"], n, p=[0.5, 0.25, 0.25]))
weight = origin.map({"USA": 3.4, "Europe": 2.6, "Japan": 2.4}) + rng.normal(0, 0.5, n)
cars = pd.DataFrame(
    {
        "origin": origin.astype("category"),
        "weight": weight.round(2),
        "mpg": (45 - 6 * weight + rng.normal(0, 2.5, n)).round(1),
    }
)

ui.page_opts(title="jupyter-scatter quick start", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Weight vs. MPG, colored by origin")

    @render_jscatter
    def plot():
        return (
            Scatter(data=cars, x="weight", y="mpg", color_by="origin")
            .axes(labels=["Weight (1000 lbs)", "MPG"])
            .lasso(initiator=True)
        )

    @render.text
    def n_selected():
        return f"{len(plot.selected())} of {len(cars)} selected"
