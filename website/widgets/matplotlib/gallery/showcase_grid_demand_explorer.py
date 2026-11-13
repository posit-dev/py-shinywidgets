# Grid demand explorer
#
# A year of synthetic hourly power demand with a seasonal cycle, a daily
# double-peak, quiet weekends, and two heat waves. Zoom into any window on the
# main chart (the toolbar's zoom-to-rectangle tool, or scroll-zoom) and the
# panel below -- the average daily profile -- redraws in place to describe
# only what's visible: "zoom is a query". Click anywhere on the main chart to
# pin the exact reading. A smoothing slider restyles the series in place,
# without losing your zoom.
#
# Bucket: showcase
# Run: uv run shiny run docs/widget-guides/matplotlib/gallery/showcase_grid_demand_explorer.py
# Data: synthesized in this file with numpy/pandas; no download needed.
#
# A plain top-level docstring would render as a text output in Shiny Express
# (bare expressions are auto-displayed), so this header is a comment instead.

import numpy as np
import pandas as pd
from matplotlib.dates import date2num, num2date
from matplotlib.figure import Figure
from shiny import reactive, req
from shiny import ui as core_ui
from shiny.express import input, render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True, title="Grid demand explorer")

hours = pd.date_range("2025-01-01", periods=24 * 365, freq="h")
hour_of_day = hours.hour.to_numpy()
doy = hours.dayofyear.to_numpy()
rng = np.random.default_rng(42)
demand = (
    100
    + 20 * np.sin(2 * np.pi * (doy - 15) / 365)
    + 15 * np.sin(2 * np.pi * (hour_of_day - 6) / 24)
    + 10 * np.sin(4 * np.pi * (hour_of_day - 8) / 24)
    - 15 * (hours.dayofweek.to_numpy() >= 5)
    + rng.normal(0, 2.5, len(hours))
)
for center in (195, 215):  # two mid-July heat waves
    demand += 18 * np.exp(-0.5 * ((doy - center) / 2.5) ** 2)

with ui.sidebar():
    ui.input_slider("smooth", "Smoothing (hours)", 0, 72, 0, step=6)
    ui.markdown(
        "Drag the toolbar's **zoom-to-rectangle** tool over a window, or "
        "scroll to zoom. Click anywhere to pin a reading."
    )

    @render.ui
    def pinned():
        ev = req(main.clicked())
        i = int(np.clip(np.searchsorted(date2num(hours), ev.xdata), 0, len(hours) - 1))
        return core_ui.value_box(
            hours[i].strftime("%b %d, %H:00"), f"{demand[i]:.0f} MW"
        )


with ui.card(full_screen=True):
    ui.card_header("Hourly demand (MW)")

    @render_matplotlib
    def main():
        fig = Figure(layout="constrained")
        ax = fig.subplots()
        ax.plot(hours, demand, lw=0.3)
        ax.set_ylabel("MW")
        return fig


with ui.card():
    ui.card_header("Average daily profile, in the visible window")

    @render_matplotlib
    def profile():
        fig = Figure(layout="constrained", figsize=(6, 2.5))
        ax = fig.subplots()
        ax.plot(range(24), [demand.mean()] * 24)
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("MW")
        return fig


@reactive.effect
def _update_main_smoothing():
    with reactive.isolate():
        canvas = main.widget
    if canvas is None:
        return
    days = input.smooth()
    series = pd.Series(demand)
    y = series if days == 0 else series.rolling(days, center=True, min_periods=1).mean()
    canvas.figure.axes[0].lines[0].set_ydata(y.to_numpy())
    canvas.draw_idle()


@reactive.effect
def _update_profile():
    (x0, x1), _ = main.limits()
    with reactive.isolate():
        canvas = profile.widget
    if canvas is None:
        return
    start = pd.Timestamp(num2date(x0).replace(tzinfo=None))
    end = pd.Timestamp(num2date(x1).replace(tzinfo=None))
    mask = (hours >= start) & (hours <= end)
    if mask.sum() == 0:
        return
    by_hour = pd.Series(demand[mask], index=hour_of_day[mask]).groupby(level=0).mean()
    by_hour = by_hour.reindex(range(24))
    ax = canvas.figure.axes[0]
    ax.lines[0].set_ydata(by_hour.to_numpy())
    ax.relim()
    ax.autoscale_view()
    canvas.draw_idle()


@reactive.effect
def _hide_footer():
    # header_visible is already False by default; only the footer
    # (cursor-position readout) needs hiding explicitly.
    with reactive.isolate():
        for w in (main.widget, profile.widget):
            if w is not None:
                w.footer_visible = False
