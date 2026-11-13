import numpy as np
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

# matplotlib's own widgets (selectors, sliders, buttons, ...) work unmodified:
# their callbacks are plain Python functions, so they can set reactive values.
rng = np.random.default_rng(2)
weight = rng.uniform(1.5, 5.0, 150)
mpg = 45 - 6 * weight + rng.normal(0, 2.5, 150)
n_selected = reactive.value(0)


@render_matplotlib
def plot():
    fig = Figure(layout="constrained")
    ax = fig.subplots()
    points = ax.scatter(weight, mpg, alpha=0.7)
    ax.set_xlabel("Weight (1000 lbs)")
    ax.set_ylabel("Miles per gallon")

    def on_select(press, release):
        x0, x1 = sorted([press.xdata, release.xdata])
        y0, y1 = sorted([press.ydata, release.ydata])
        mask = (weight >= x0) & (weight <= x1) & (mpg >= y0) & (mpg <= y1)
        points.set_facecolors(np.where(mask, "tab:orange", "tab:blue"))
        fig.canvas.draw_idle()
        n_selected.set(int(mask.sum()))

    # Keep a reference: matplotlib selectors stop working once garbage collected
    fig._selector = RectangleSelector(ax, on_select, interactive=True)
    return fig


@render.text
def summary():
    return f"{n_selected()} cars in the box"
