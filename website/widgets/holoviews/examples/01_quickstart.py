# A quick-start hvPlot scatter: one line of pandas turns into an interactive
# Bokeh plot (pan, zoom, hover) with no extra ceremony.
import plotly.express as px
import hvplot.pandas  # noqa: F401 -- registers the .hvplot accessor on DataFrames
from shiny.express import ui

from shinywidgets import render_holoviews

tips = px.data.tips()

ui.page_opts(title="Tips, by total bill and tip", fillable=True)


@render_holoviews
def scatter():
    return tips.hvplot.scatter(
        "total_bill",
        "tip",
        by="day",
        responsive=True,
        title="Tips vs. total bill",
        hover_cols=["size"],
    )
