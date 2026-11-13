import numpy as np
import pandas as pd
from matplotlib.dates import num2date
from matplotlib.figure import Figure
from shiny.express import render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

# Two years of hourly demand with a seasonal cycle, a daily double-peak, and
# quiet weekends -- the kind of series where "what happened in this window?"
# only makes sense once you've zoomed into it.
hours = pd.date_range("2024-01-01", periods=24 * 365 * 2, freq="h")
hour_of_day = hours.hour.to_numpy()
rng = np.random.default_rng(3)
demand = (
    100
    + 20 * np.sin(2 * np.pi * hours.dayofyear.to_numpy() / 365)
    + 15 * np.sin(2 * np.pi * (hour_of_day - 6) / 24)
    + 10 * np.sin(4 * np.pi * (hour_of_day - 8) / 24)
    - 15 * (hours.dayofweek.to_numpy() >= 5)
    + rng.normal(0, 3, len(hours))
)


@render_matplotlib
def plot():
    fig = Figure(layout="constrained")
    ax = fig.subplots()
    ax.plot(hours, demand, lw=0.3)
    ax.set_ylabel("Demand (MW)")
    return fig


@render.code
def summary():
    (x0, x1), _ = plot.limits()
    start, end = num2date(x0).replace(tzinfo=None), num2date(x1).replace(tzinfo=None)
    mask = (hours >= pd.Timestamp(start)) & (hours <= pd.Timestamp(end))
    visible = demand[mask]
    if visible.size == 0:
        return "Zoom in to see a summary of the visible window"
    return (
        f"{visible.size} hours visible\n"
        f"mean {visible.mean():.1f} MW, peak {visible.max():.1f} MW"
    )
