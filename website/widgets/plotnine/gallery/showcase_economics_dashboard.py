# Title: US economy, 1967-2015
# Bucket: showcase
# One-line: A 50-year time series you zoom into, with a linked "what
# happened here" plot, a markable month, and a theme switcher that keeps
# your zoom and mark across the re-render.
# Run: uv run --no-sync shiny run showcase_economics_dashboard.py
# Data: plotnine.data.economics (ships with plotnine)
#
# Note: this header is a comment, not a module docstring -- Shiny Express
# renders a bare top-level string literal as page content.

import matplotlib.dates as mdates
import pandas as pd
from plotnine import (
    aes,
    geom_line,
    geom_vline,
    ggplot,
    labs,
    theme_538,
    theme_bw,
    theme_minimal,
)
from plotnine.data import economics
from shiny import reactive, req
from shiny.express import input, render, ui
from shinywidgets import render_plotnine

THEMES = {"minimal": theme_minimal, "bw": theme_bw, "538": theme_538}

ui.page_opts(title="US economy, 1967-2015", fillable=True)
view = reactive.value((economics.date.min(), economics.date.max()))
picked = reactive.value(None)

ui.input_select("theme", "Theme", list(THEMES), selected="minimal")

with ui.layout_columns(col_widths=(8, 4, 8, 4)):
    with ui.card(full_screen=True):
        ui.card_header("Unemployment -- zoom in, click to mark a month")

        @render_plotnine
        def top():
            marked = picked()
            p = (
                ggplot(economics, aes("date", "unemploy"))
                + geom_line()
                + labs(x="", y="Unemployed (thousands)")
                + THEMES[input.theme()]()
            )
            # The mark is an ordinary plotnine layer: clicking sets `picked`,
            # and the re-render draws the vline at the clicked month
            if marked is not None:
                p += geom_vline(xintercept=marked, color="firebrick", linetype="dashed")
            return p

    with ui.layout_columns(col_widths=12, fill=False):
        with ui.value_box(theme="primary"):
            "Visible window"

            @render.text
            def window_label():
                lo, hi = view()
                return f"{lo:%b %Y} - {hi:%b %Y}"

        with ui.value_box():
            "Average unemployment (visible)"

            @render.text
            def avg_unemployment():
                lo, hi = view()
                visible = economics[(economics.date >= lo) & (economics.date <= hi)]
                return f"{visible.unemploy.mean():,.0f}k"

    with ui.card(full_screen=True):
        ui.card_header("Savings rate, same window")

        @render_plotnine
        def bottom():
            lo, hi = view()
            visible = economics[(economics.date >= lo) & (economics.date <= hi)]
            return (
                ggplot(visible, aes("date", "psavert"))
                + geom_line(color="darkorange")
                + labs(x="", y="Personal savings rate (%)")
                + THEMES[input.theme()]()
            )

    with ui.value_box():
        "Marked month"

        @render.text
        def marked_label():
            m = picked()
            return "none yet -- click the top plot" if m is None else f"{m:%B %Y}"


skip_next_track = [False]


@reactive.effect(priority=10)
def _restore_view():
    # A theme switch (or a new mark) rebuilds the figure from scratch.
    # `limits()` re-seeds to the new figure's full extent on every render
    # (it's inherent widget state, not something the user did) -- re-apply
    # the stored zoom on top of that seed, and push the zoom onto the
    # toolbar's history so Home still restores the full range. Runs at a
    # higher priority than `_track_view` so the re-seed never reaches `view`;
    # `skip_next_track` also discards the one `limits()` publish this
    # restore's own `set_xlim` triggers, so only genuine zooms update `view`.
    # The mark needs no restore: it's a `geom_vline` layer in `top()` itself.
    canvas = top.widget
    req(canvas)
    with reactive.isolate():
        lo, hi = view()
    ax = canvas.figure.axes[0]
    canvas.toolbar.push_current()
    ax.set_xlim(mdates.date2num(lo), mdates.date2num(hi))
    canvas.draw_idle()
    skip_next_track[0] = True


@reactive.effect
def _track_view():
    (x0, x1), _ = top.limits()
    if skip_next_track[0]:
        skip_next_track[0] = False
        return
    lo = pd.Timestamp(mdates.num2date(x0).replace(tzinfo=None))
    hi = pd.Timestamp(mdates.num2date(x1).replace(tzinfo=None))
    view.set((lo, hi))


@reactive.effect
def _mark_click():
    # Click -> derive the month -> feed it back into `top()`'s render, which
    # re-renders once with the vline (a re-render doesn't re-run this effect
    # on the unchanged click, so there's no loop). `_restore_view` keeps the
    # zoom across that re-render, exactly as it does for a theme switch.
    event = top.clicked()
    req(event)
    month = pd.Timestamp(mdates.num2date(event.xdata).replace(tzinfo=None)).replace(
        day=1
    )
    picked.set(month)
