import numpy as np
from bokeh.layouts import gridplot
from bokeh.plotting import figure
from shiny.express import ui
from shinywidgets import render_bokeh

ui.page_opts(title="Bokeh layouts", fillable=True)

rng = np.random.default_rng(0)
x = rng.normal(size=300)
y = x * 0.6 + rng.normal(size=300)


@render_bokeh
def grid():
    scatter = figure(title="x vs. y", sizing_mode="stretch_both")
    scatter.scatter(x, y, size=6, alpha=0.6)

    hx, ex = np.histogram(x, bins=20)
    hist_x = figure(title="histogram of x", sizing_mode="stretch_both")
    hist_x.quad(top=hx, bottom=0, left=ex[:-1], right=ex[1:])

    hy, ey = np.histogram(y, bins=20)
    hist_y = figure(title="histogram of y", sizing_mode="stretch_both")
    hist_y.quad(top=hy, bottom=0, left=ey[:-1], right=ey[1:], fill_color="firebrick")

    cum = figure(title="cumulative mean of y", sizing_mode="stretch_both")
    cum.line(np.arange(len(y)), np.cumsum(y) / np.arange(1, len(y) + 1), line_width=2)

    return gridplot(
        [[scatter, hist_x], [hist_y, cum]], sizing_mode="stretch_both"
    )
