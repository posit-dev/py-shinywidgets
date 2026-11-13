import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny.express import ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(4)
n = 500
origin = pd.Series(rng.choice(["USA", "Europe", "Japan"], n, p=[0.5, 0.25, 0.25]))
weight = origin.map({"USA": 3.4, "Europe": 2.6, "Japan": 2.4}) + rng.normal(0, 0.5, n)
cars = pd.DataFrame(
    {
        "model": [f"Car {i}" for i in range(n)],
        "origin": origin.astype("category"),
        "weight": weight.round(2),
        "mpg": (45 - 6 * weight + rng.normal(0, 2.5, n)).round(1),
    }
)

ui.page_opts(title="Tooltips", fillable=True)
ui.p("Hover a point to see its data, right in the plot.")

with ui.card(full_screen=True):

    @render_jscatter
    def plot():
        return (
            Scatter(data=cars, x="weight", y="mpg", color_by="origin")
            .tooltip(True, properties=["x", "y", "color", "model"])
        )
