# Accessors default to a 250ms debounce (brush selectors stream updates
# mid-drag). rate_policy/rate_delay on the decorator change that per output.
import bqplot
from bqplot.interacts import BrushIntervalSelector
import numpy as np
from shiny.express import render, ui
from shinywidgets import render_bqplot

ui.page_opts(title="Rate limiting", fillable=True)

x = np.linspace(0, 10, 200)
y = np.sin(x)


def make_fig():
    x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
    line = bqplot.Lines(x=x, y=y, scales={"x": x_sc, "y": y_sc})
    return bqplot.Figure(
        marks=[line], interaction=BrushIntervalSelector(scale=x_sc, marks=[line])
    )


# Plain counters, not reactive.value: a render function may not write to a
# reactive value it also reads, or it retriggers itself in a tight loop
counts = {"debounced": 0, "throttled": 0}

with ui.layout_columns():
    with ui.card():
        ui.card_header("Default: debounce, 250ms")

        @render_bqplot
        def debounced():
            return make_fig()

        @render.code
        def debounced_label():
            debounced.brush()
            counts["debounced"] += 1
            return f"brush() re-fired {counts['debounced']} times"

    with ui.card():
        ui.card_header('rate_policy="throttle", rate_delay=0.05')

        @render_bqplot(rate_policy="throttle", rate_delay=0.05)
        def throttled():
            return make_fig()

        @render.code
        def throttled_label():
            throttled.brush()
            counts["throttled"] += 1
            return f"brush() re-fired {counts['throttled']} times"
