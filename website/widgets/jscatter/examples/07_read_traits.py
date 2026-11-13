import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny.express import render, ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(5)
n = 400
points = pd.DataFrame({"x": rng.uniform(0, 1, n), "y": rng.uniform(0, 1, n)})

ui.page_opts(title="Beyond the accessor: .read()", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):

        @render_jscatter
        def plot():
            return Scatter(data=points, x="x", y="y").lasso(initiator=True)

    with ui.card():
        ui.card_header("Traits plot.read() can reach")

        @render.text
        def hovering():
            idx = plot.read("hovering")
            return f"hovering: {'none' if idx is None else idx}"

        @render.text
        def zoom_level():
            return f"zoom_level: {plot.read('zoom_level'):.2f}"

        @render.text
        def lasso_polygon():
            poly = plot.read("lasso_selection_polygon")
            return f"lasso_selection_polygon: {'none' if poly is None else f'{len(poly)} vertices'}"
