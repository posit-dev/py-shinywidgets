import bqplot
import numpy as np
import pandas as pd
from bqplot.interacts import BrushSelector
from shiny.express import render, ui
from shinywidgets import render_bqplot

ui.page_opts(title="Reading selected_rows() on demand", fillable=True)

rng = np.random.default_rng(0)
points = pd.DataFrame(
    {"x": rng.uniform(0, 10, 300), "y": rng.uniform(0, 10, 300)}
)
x, y = points["x"], points["y"]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Brush a region, then download -- no need to click anything first")

        @render_bqplot
        def plot():
            x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
            scatter = bqplot.Scatter(x=x, y=y, scales={"x": x_sc, "y": y_sc})
            return bqplot.Figure(
                marks=[scatter],
                interaction=BrushSelector(x_scale=x_sc, y_scale=y_sc, marks=[scatter]),
            )

    with ui.card():

        @render.download_button(
            filename="brushed.csv", label="Download brushed points as CSV"
        )
        def download():
            # selected_rows() is live from the moment the figure renders, so
            # this reads whatever's currently brushed, even on its first run.
            yield plot.selected_rows(points).to_csv(index=False)
