import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny.express import render, ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(1)
n = 2000
points = pd.DataFrame({"x": rng.uniform(0, 1, n), "y": rng.uniform(0, 1, n)})

ui.page_opts(title="Reading selected_rows() on demand", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Lasso some points, then download -- no need to click anything first")

        @render_jscatter
        def plot():
            return Scatter(data=points, x="x", y="y").lasso(initiator=True)

    with ui.card():

        @render.download_button(
            filename="selected.csv", label="Download selected points as CSV"
        )
        def download():
            # selected_rows() is seeded empty the moment the plot renders, so
            # this reads whatever's currently selected, even on first run.
            yield plot.selected_rows().to_csv(index=False)
