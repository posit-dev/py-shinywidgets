# Draggable marks: enable_move lets users pull points around. x/y land back
# in Python once the drag ends (set update_on_move=True to stream mid-drag).
import bqplot
import numpy as np
from shiny.express import render, ui
from shinywidgets import reactive_read, render_bqplot

ui.page_opts(title="Draggable points", fillable=True)

rng = np.random.default_rng(2)
x0 = np.linspace(1, 10, 12)
y0 = 2 * x0 + rng.normal(0, 2, 12)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bqplot
        def plot():
            x_sc = bqplot.LinearScale(min=0, max=11)
            y_sc = bqplot.LinearScale(min=-5, max=30)
            points = bqplot.Scatter(
                x=x0.copy(),
                y=y0.copy(),
                scales={"x": x_sc, "y": y_sc},
                colors=["#4c78a8"],
                default_size=80,
                enable_move=True,
            )
            fit = bqplot.Lines(
                x=[0, 11],
                y=[0, 22],
                scales={"x": x_sc, "y": y_sc},
                colors=["#e45756"],
                stroke_width=2,
                line_style="dashed",
            )
            return bqplot.Figure(marks=[points, fit], title="Drag a point")

    with ui.card():
        ui.card_header("Fit after dragging")

        @render.code
        def fit_summary():
            points = plot.widget.marks[0]
            x = reactive_read(points, "x")
            y = reactive_read(points, "y")
            slope, intercept = np.polyfit(x, y, 1)

            # In-place update: mutate the existing Lines mark rather than
            # re-rendering the figure, so the drag the user just made stays put
            fit = plot.widget.marks[1]
            xs = np.array([0.0, 11.0])
            fit.x, fit.y = xs, slope * xs + intercept

            return f"y = {slope:.2f}x + {intercept:.2f}"
