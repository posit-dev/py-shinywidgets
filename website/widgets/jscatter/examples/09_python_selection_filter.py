import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(1)
n = 3000
origin = pd.Series(rng.choice(["USA", "Europe", "Japan"], n, p=[0.5, 0.25, 0.25]))
weight = origin.map({"USA": 3.4, "Europe": 2.6, "Japan": 2.4}) + rng.normal(0, 0.5, n)
cars = pd.DataFrame({"origin": origin.astype("category"), "weight": weight.round(2)})
cars["mpg"] = (45 - 6 * cars["weight"] + rng.normal(0, 2.5, n)).round(1)

ui.page_opts(title="Drive selection and filter from Python", fillable=True)
with ui.layout_columns(col_widths=[4, 4, 4]):
    ui.input_action_button("select_heavy", "Select heaviest 10%")
    ui.input_action_button("filter_usa", "Filter to USA only")
    ui.input_action_button("reset", "Reset")

with ui.card(full_screen=True):

    @render_jscatter
    def plot():
        return Scatter(data=cars, x="weight", y="mpg", color_by="origin")

    @reactive.effect
    @reactive.event(input.select_heavy)
    def _select():
        cutoff = cars["weight"].quantile(0.9)
        ids = np.flatnonzero(cars["weight"] >= cutoff).astype("uint32")
        with reactive.isolate():
            plot.widget.selection = ids

    @reactive.effect
    @reactive.event(input.filter_usa)
    def _filter():
        ids = np.flatnonzero(cars["origin"] == "USA").astype("uint32")
        with reactive.isolate():
            plot.widget.filter = ids

    @reactive.effect
    @reactive.event(input.reset)
    def _reset():
        with reactive.isolate():
            plot.widget.selection = np.array([], dtype="uint32")
            plot.widget.filter = None

    @render.text
    def n_selected():
        return f"{len(plot.selected()):,} selected"
