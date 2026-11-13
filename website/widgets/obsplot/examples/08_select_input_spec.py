from __future__ import annotations

import polars as pl
from pyobsplot import Plot
from shiny.express import input, ui

from shinywidgets import render_obsplot

ui.page_opts(title="Driving the spec from a Shiny input", fillable=True)

penguins = pl.read_csv(
    "https://github.com/juba/pyobsplot/raw/main/doc/data/penguins.csv"
)

VIEWS = {
    "Scatter": lambda: [
        Plot.dot(
            penguins,
            {"x": "flipper_length_mm", "y": "body_mass_g", "fill": "species"},
        ),
    ],
    "Scatter + regression": lambda: [
        Plot.dot(
            penguins,
            {"x": "flipper_length_mm", "y": "body_mass_g", "fill": "species"},
        ),
        Plot.linearRegressionY(
            penguins,
            {"x": "flipper_length_mm", "y": "body_mass_g", "stroke": "species"},
        ),
    ],
    "Density contours": lambda: [
        Plot.density(
            penguins,
            {"x": "flipper_length_mm", "y": "body_mass_g", "stroke": "species"},
        ),
    ],
}

ui.input_select("view", "View", choices=list(VIEWS))

with ui.card(full_screen=True):

    @render_obsplot
    def plot():
        return Plot.plot(
            {
                "grid": True,
                "color": {"legend": True},
                "marks": VIEWS[input.view()](),
            }
        )
