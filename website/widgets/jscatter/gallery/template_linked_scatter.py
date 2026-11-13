# Assigning to __doc__ (rather than a bare string literal) keeps this header
# out of the rendered page: shiny.express displays every top-level expression
# statement's value, docstrings included.
__doc__ = """
Linked scatter plots with a selection table (template)

Two jupyter-scatter plots share a lasso selection, and a table shows the
selected rows. Swap in your own data frame and column names to adapt it.

Run: shiny run template_linked_scatter.py
Data: synthetic car-like data (generated below); no download needed.
"""

import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(1)
n = 5000
origin = pd.Series(rng.choice(["USA", "Europe", "Japan"], n, p=[0.5, 0.25, 0.25]))
weight = origin.map({"USA": 3.4, "Europe": 2.6, "Japan": 2.4}) + rng.normal(0, 0.5, n)
cars = pd.DataFrame(
    {
        "origin": origin.astype("category"),
        "weight": weight.round(2),
        "mpg": (45 - 6 * weight + rng.normal(0, 2.5, n)).round(1),
        "hp": (45 * weight + rng.normal(0, 25, n)).round(),
    }
)

ui.page_opts(title="Linked jscatter plots", fillable=True)
ui.p(
    "Drag with the lasso tool (or press and hold, then drag) on either plot "
    "to select points. The selection shows up in the other plot and the "
    "table, through a reactive accessor on the Python side.",
    class_="text-muted small mb-0",
)

with ui.layout_columns(col_widths=[4, 4, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Weight vs. MPG")

        @render_jscatter
        def weight_mpg():
            return (
                Scatter(data=cars, x="weight", y="mpg", color_by="origin")
                .axes(labels=["Weight (1000 lbs)", "MPG"])
                .lasso(initiator=True)
            )

    with ui.card(full_screen=True):
        ui.card_header("Horsepower vs. MPG")

        @render_jscatter
        def hp_mpg():
            return (
                Scatter(data=cars, x="hp", y="mpg", color_by="origin")
                .axes(labels=["Horsepower", "MPG"])
                .lasso(initiator=True)
            )

    with ui.card(full_screen=True):

        @render.text
        def n_selected():
            return f"{len(weight_mpg.selected()):,} of {len(cars):,} cars selected"

        @render.data_frame
        def selected_cars():
            return weight_mpg.selected_rows()


# Linked brushing: mirror each plot's selection onto the other one
def link(source, target):
    @reactive.effect
    def _():
        selection = source.selected()
        with reactive.isolate():
            if not np.array_equal(selection, target.widget.selection):
                target.widget.selection = selection


link(weight_mpg, hp_mpg)
link(hp_mpg, weight_mpg)
