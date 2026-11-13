import numpy as np
from matplotlib.figure import Figure
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

t = np.linspace(0, 10, 300)
y = np.sin(t)
hover = reactive.value("move the mouse over the plot")


@render_matplotlib
def plot():
    fig = Figure(layout="constrained")
    ax = fig.subplots()
    ax.plot(t, y)

    def on_move(event):
        if event.inaxes is None:
            return
        hover.set(f"x={event.xdata:.2f}  y={event.ydata:.2f}")

    fig.canvas.mpl_connect("motion_notify_event", on_move)
    return fig


@render.code
def coords():
    return hover()
