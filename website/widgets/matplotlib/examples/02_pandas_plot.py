import pandas as pd
from matplotlib.cbook import get_sample_data
from matplotlib.figure import Figure
from shiny.express import ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

# Anything that hands matplotlib a Figure or Axes comes along for free:
# pandas' own .plot() accessor, seaborn, statsmodels, scikit-learn displays, ...
# Monthly adjusted close, 1990-2020ish, bundled with matplotlib as sample data
with get_sample_data("Stocks.csv") as f:
    stocks = pd.read_csv(f, comment="#", skipinitialspace=True, parse_dates=["Date"])
stocks = stocks.set_index("Date")[["AAPL", "MSFT", "GOOGL"]].dropna()


@render_matplotlib
def plot():
    fig = Figure(layout="constrained", figsize=(7, 4))
    ax = fig.subplots()
    stocks.plot(ax=ax, logy=True)
    ax.set_ylabel("Adjusted close ($, log scale)")
    return fig
