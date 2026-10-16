from bokeh.plotting import figure
from shiny.express import ui
from shinywidgets import render_bokeh

ui.h2("Bokeh outputs")


@render_bokeh
def plot() -> figure:
    chart = figure(width=300, height=200)
    chart.line([1, 2, 3], [1, 4, 9])
    return chart
