# Zoom-and-click starter
#
# A minimal starting point for an interactive matplotlib dashboard: zoom or pan
# on the chart and a summary panel describes what's visible; click a point to
# pin its exact value. Swap in your own data and keep the two accessor-driven
# outputs.
#
# Bucket: template
# Run: uv run shiny run docs/widget-guides/matplotlib/gallery/template_zoom_and_click.py
# Data: synthesized in this file with numpy; no download needed.
#
# A plain top-level docstring would render as a text output in Shiny Express
# (bare expressions are auto-displayed), so this header is a comment instead.

import numpy as np
from matplotlib.figure import Figure
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

t = np.linspace(0, 50, 4000)
y = np.sin(t) + 0.3 * np.sin(5 * t) + 0.02 * t**1.2

with ui.layout_columns(col_widths=(8, 4, 4)):
    with ui.card(full_screen=True):
        ui.card_header("Zoom or pan to inspect")

        @render_matplotlib
        def plot():
            fig = Figure(layout="constrained")
            ax = fig.subplots()
            ax.plot(t, y, lw=0.8)
            return fig

    with ui.card():
        ui.card_header("Visible window")

        @render.code
        def window_summary():
            (x0, x1), (y0, y1) = plot.limits()
            mask = (t >= x0) & (t <= x1)
            return (
                f"x: {x0:.1f} to {x1:.1f}\n"
                f"{mask.sum()} points visible\n"
                f"mean y: {y[mask].mean():.2f}"
                if mask.any()
                else "nothing in view"
            )

    with ui.card():
        ui.card_header("Pinned reading")

        @render.code
        def pinned():
            ev = req(plot.clicked())
            return f"x={ev.xdata:.2f}  y={ev.ydata:.2f}"
