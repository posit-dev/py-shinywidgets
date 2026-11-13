import numpy as np
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="Update in place", fillable=True)

rng = np.random.default_rng(4)
full_x, full_y = rng.normal(size=200), rng.normal(size=200)
src = ColumnDataSource({"x": full_x, "y": full_y})

with ui.card(full_screen=True):
    ui.input_slider("n", "Number of points", min=20, max=200, value=200, step=20)

    @render_bokeh
    def plot():
        p = figure(title="Pan or zoom, then move the slider")
        p.scatter("x", "y", source=src, size=6, alpha=0.6)
        return p


@reactive.effect
def _():
    # Mutates the existing ColumnDataSource instead of returning a new
    # figure, so the user's current zoom/pan survives the update.
    n = input.n()
    src.data = {"x": full_x[:n], "y": full_y[:n]}
