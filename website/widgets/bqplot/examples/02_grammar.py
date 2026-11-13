# The grammar: scales map data to pixels, marks draw on top of scales, axes
# render the scales. Two marks sharing one pair of scales stay aligned.
import bqplot
import numpy as np
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_bqplot

ui.page_opts(title="bqplot grammar", fillable=True)

tips = px.data.tips()

with ui.card(full_screen=True):

    @render_bqplot
    def plot():
        x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()

        points = bqplot.Scatter(
            x=tips["total_bill"],
            y=tips["tip"],
            scales={"x": x_sc, "y": y_sc},
            colors=["#4c78a8"],
            default_opacities=[0.6],
        )

        # A second mark on the *same* scales: a least-squares fit line
        slope, intercept = np.polyfit(tips["total_bill"], tips["tip"], 1)
        xs = np.array([tips["total_bill"].min(), tips["total_bill"].max()])
        fit = bqplot.Lines(
            x=xs,
            y=slope * xs + intercept,
            scales={"x": x_sc, "y": y_sc},
            colors=["#e45756"],
            stroke_width=3,
        )

        return bqplot.Figure(
            marks=[points, fit],
            axes=[
                bqplot.Axis(scale=x_sc, label="Total bill ($)"),
                bqplot.Axis(scale=y_sc, orientation="vertical", label="Tip ($)"),
            ],
            title="Two marks, one pair of scales",
        )
