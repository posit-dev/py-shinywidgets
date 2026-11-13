# Beyond the accessors: reactive_read() on any trait. "brushing" is True only
# while the mouse button is down, so gate expensive work on it going False.
# A PanZoom's scales report the zoomed-in domain as the user pans.
import bqplot
from bqplot.interacts import BrushIntervalSelector, PanZoom
import numpy as np
from shiny import req
from shiny.express import render, ui
from shinywidgets import reactive_read, render_bqplot

ui.page_opts(title="reactive_read()", fillable=True)

rng = np.random.default_rng(0)
x = np.sort(rng.uniform(0, 100, 500))
y = rng.normal(0, 1, 500).cumsum()

with ui.layout_columns():
    with ui.card():
        ui.card_header('Gate on "brushing" to skip mid-drag work')

        @render_bqplot
        def brushed():
            x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
            line = bqplot.Lines(x=x, y=y, scales={"x": x_sc, "y": y_sc})
            return bqplot.Figure(
                marks=[line],
                interaction=BrushIntervalSelector(scale=x_sc, marks=[line]),
            )

        @render.code
        def gated_mean():
            brush = brushed.widget.interaction
            selected = reactive_read(brush, "selected")
            req(selected is not None)
            req(not reactive_read(brush, "brushing"))  # wait for mouseup
            lo, hi = sorted(selected.tolist())
            mask = (x >= lo) & (x <= hi)
            return f"mean y in [{lo:.1f}, {hi:.1f}]: {y[mask].mean():.2f}"

    with ui.card():
        ui.card_header("Read the zoomed domain from PanZoom")

        @render_bqplot
        def zoomable():
            x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
            line = bqplot.Lines(x=x, y=y, scales={"x": x_sc, "y": y_sc})
            return bqplot.Figure(
                marks=[line],
                interaction=PanZoom(scales={"x": [x_sc], "y": [y_sc]}),
            )

        @render.code
        def visible_domain():
            x_sc = zoomable.widget.marks[0].scales["x"]
            lo = reactive_read(x_sc, "min")
            hi = reactive_read(x_sc, "max")
            return f"visible x range: {lo}-{hi}" if lo is not None else "unzoomed"
