import numpy as np
from matplotlib.figure import Figure
from shiny.express import render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

t = np.linspace(0, 100, 5000)
y = np.sin(t) + 0.05 * t


@render_matplotlib
def plot():
    fig = Figure(layout="constrained")
    ax = fig.subplots()
    ax.plot(t, y, lw=0.8)
    return fig


@render.code
def window():
    (x0, x1), (y0, y1) = plot.limits()
    return f"x: {x0:.1f} to {x1:.1f}\ny: {y0:.2f} to {y1:.2f}"
