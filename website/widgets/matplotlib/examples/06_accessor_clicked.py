import numpy as np
from matplotlib.figure import Figure
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

t = np.linspace(0, 10, 300)
signal = np.sin(t) + 0.15 * np.random.default_rng(0).standard_normal(300)


@render_matplotlib
def plot():
    fig = Figure(layout="constrained")
    ax = fig.subplots()
    ax.plot(t, signal, lw=1)
    return fig


@render.code
def reading():
    ev = req(plot.clicked())
    return f"x={ev.xdata:.2f}  y={ev.ydata:.2f}"
