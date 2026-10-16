import hvplot.pandas  # noqa: F401
import pandas as pd
import panel as pn
from bokeh.plotting import figure
from holoviews import Scatter
from shiny.express import ui
from shinywidgets import render_bokeh, render_hvplot, render_panel

ui.h2("Bokeh outputs")


@render_bokeh
def plot() -> figure:
    chart = figure(width=300, height=200)
    chart.line([1, 2, 3], [1, 4, 9])
    return chart


@render_panel
def table() -> pn.widgets.Tabulator:
    return pn.widgets.Tabulator(pd.DataFrame({"x": [1, 2, 3]}))


@render_hvplot
def scatter() -> Scatter:
    return pd.DataFrame({"x": [1, 2, 3], "y": [1, 4, 9]}).hvplot.scatter(x="x", y="y")
