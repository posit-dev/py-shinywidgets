import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny.express import ui
from shinywidgets import render_itables, render_jscatter

rng = np.random.default_rng(1)
n = 1500
origin = pd.Series(rng.choice(["USA", "Europe", "Japan"], n, p=[0.5, 0.25, 0.25]))
weight = origin.map({"USA": 3.4, "Europe": 2.6, "Japan": 2.4}) + rng.normal(0, 0.5, n)
cars = pd.DataFrame({"origin": origin.astype("category"), "weight": weight.round(2)})
cars["mpg"] = (45 - 6 * cars["weight"] + rng.normal(0, 2.5, n)).round(1)

ui.page_opts(title="Lasso selection drives an itables table", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):

        @render_jscatter
        def plot():
            return Scatter(data=cars, x="weight", y="mpg", color_by="origin").lasso(
                initiator=True
            )

    with ui.card(full_screen=True):
        ui.card_header("Rows inside the lasso")

        @render_itables
        def table():
            return plot.selected_rows()
