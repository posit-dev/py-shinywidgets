import numpy as np
from matplotlib.cbook import get_sample_data
from matplotlib.dates import date2num
from matplotlib.figure import Figure
from shiny import req
from shiny import ui as core_ui
from shiny.express import render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

goog = get_sample_data("goog.npz")["price_data"]


@render_matplotlib
def plot():
    fig = Figure(layout="constrained")
    ax = fig.subplots()
    ax.plot(goog["date"], goog["close"], lw=0.8)
    ax.set_ylabel("Close ($)")
    return fig


@render.ui
def detail():
    ev = req(plot.clicked())
    i = int(
        np.clip(np.searchsorted(date2num(goog["date"]), ev.xdata), 0, len(goog) - 1)
    )
    date = goog["date"][i]
    return core_ui.value_box(
        f"{date.item().strftime('%b %d, %Y')}", f"${goog['close'][i]:.2f}"
    )
