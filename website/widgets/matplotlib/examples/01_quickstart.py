from matplotlib.cbook import get_sample_data
from matplotlib.figure import Figure
from shiny.express import ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

# Google's daily closing price from its 2004 IPO through the 2008 crash,
# bundled with matplotlib as sample data
goog = get_sample_data("goog.npz")["price_data"]


@render_matplotlib
def plot():
    fig = Figure(layout="constrained")
    ax = fig.subplots()
    ax.plot(goog["date"], goog["close"])
    ax.set_ylabel("Close ($)")
    return fig
