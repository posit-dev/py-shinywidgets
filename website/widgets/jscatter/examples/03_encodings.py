import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny.express import ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(3)
n = 4000
origin = pd.Series(rng.choice(["USA", "Europe", "Japan"], n, p=[0.5, 0.25, 0.25]))
weight = origin.map({"USA": 3.4, "Europe": 2.6, "Japan": 2.4}) + rng.normal(0, 0.5, n)
cars = pd.DataFrame(
    {
        "origin": origin.astype("category"),
        "weight": weight.round(2),
        "mpg": (45 - 6 * weight + rng.normal(0, 2.5, n)).round(1),
        "hp": (45 * weight + rng.normal(0, 25, n)).round(),
    }
)

ui.page_opts(title="Color, size, and opacity encodings", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Color = origin, size and opacity = horsepower")

    @render_jscatter
    def plot():
        # jscatter allows at most 2 distinct *data dimensions* driving
        # color/size/opacity at once; reuse one dimension (here "hp") across
        # more than one channel to combine three encodings anyway.
        return (
            Scatter(data=cars, x="weight", y="mpg")
            .color(by="origin")
            .size(by="hp", map=[2, 4, 6, 8, 10])
            .opacity(by="hp")
            .legend(True)
        )
