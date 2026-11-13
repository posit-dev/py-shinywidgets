import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny.express import ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(7)
points = pd.DataFrame({"x": rng.uniform(0, 1, 500), "y": rng.uniform(0, 1, 500)})

ui.page_opts(title="Fill vs. fixed height", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Fills the card")

        @render_jscatter
        def fills():
            return Scatter(data=points, x="x", y="y")

    with ui.card():
        ui.card_header("Fixed height (300px)")

        @render_jscatter
        def fixed():
            return Scatter(data=points, x="x", y="y", height=300)
