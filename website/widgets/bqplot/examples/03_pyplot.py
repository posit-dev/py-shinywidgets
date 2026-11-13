# The same plot through bqplot.pyplot's matplotlib-like shortcuts. Always
# call bplt.figure() first and return its result -- see "Gotchas" for why.
import bqplot.pyplot as bplt
import numpy as np
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_bqplot

ui.page_opts(title="bqplot.pyplot", fillable=True)

tips = px.data.tips()

with ui.card(full_screen=True):

    @render_bqplot
    def plot():
        fig = bplt.figure(title="Two marks, one pair of scales")
        bplt.scatter(
            tips["total_bill"],
            tips["tip"],
            colors=["#4c78a8"],
            default_opacities=[0.6],
        )
        slope, intercept = np.polyfit(tips["total_bill"], tips["tip"], 1)
        xs = np.array([tips["total_bill"].min(), tips["total_bill"].max()])
        bplt.plot(xs, slope * xs + intercept, colors=["#e45756"], stroke_width=3)
        bplt.xlabel("Total bill ($)")
        bplt.ylabel("Tip ($)")
        return fig
