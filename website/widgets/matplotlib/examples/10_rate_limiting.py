import numpy as np
from matplotlib.figure import Figure
from shiny.express import render, ui
from shinywidgets import as_widget, render_matplotlib

ui.page_opts(fillable=True)

t = np.linspace(0, 10, 2000)
y = np.sin(t)
counts = {"default": 0, "fast": 0}


def make_plot():
    fig = Figure(layout="constrained", figsize=(4, 3))
    ax = fig.subplots()
    ax.plot(t, y)
    canvas = as_widget(fig)
    canvas.toolbar_visible = "visible"  # skip the hover-to-reveal fade
    return canvas


with ui.layout_columns():
    with ui.card():
        ui.card_header("default: debounced 250ms")

        @render_matplotlib
        def default_out():
            return make_plot()

        @render.code
        def default_count():
            default_out.limits()
            counts["default"] += 1
            return f"limits() recomputed {counts['default']} times"

    with ui.card():
        ui.card_header("rate_delay=0: every event")

        @render_matplotlib(rate_delay=0)
        def fast_out():
            return make_plot()

        @render.code
        def fast_count():
            fast_out.limits()
            counts["fast"] += 1
            return f"limits() recomputed {counts['fast']} times"
