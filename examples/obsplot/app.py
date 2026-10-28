from __future__ import annotations

import polars as pl
from pyobsplot import Plot
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_obsplot

penguins = pl.read_csv(
    "https://github.com/juba/pyobsplot/raw/main/doc/data/penguins.csv"
)

MARKS = {
    "dot + density": lambda: [
        Plot.dot(
            penguins,
            {"x": "flipper_length_mm", "y": "body_mass_g", "fill": "species"},
        ),
        Plot.density(
            penguins,
            {"x": "flipper_length_mm", "y": "body_mass_g", "stroke": "species"},
        ),
    ],
    "dot + tip": lambda: [
        Plot.dot(
            penguins,
            {
                "x": "flipper_length_mm",
                "y": "body_mass_g",
                "fill": "species",
                "tip": True,
            },
        )
    ],
    "regression": lambda: [
        Plot.dot(
            penguins,
            {"x": "flipper_length_mm", "y": "body_mass_g", "fill": "species"},
        ),
        Plot.linearRegressionY(
            penguins,
            {"x": "flipper_length_mm", "y": "body_mass_g", "stroke": "species"},
        ),
    ],
}

with ui.card():
    ui.card_header("Palmer penguins, Observable Plot style")
    ui.input_select("mark", "Marks", choices=list(MARKS))

    @render_obsplot
    def plot():
        return Plot.plot(
            {
                "grid": True,
                "color": {"legend": True},
                "marks": MARKS[input.mark()](),
            }
        )


# Update the chart in place (no re-render) by assigning a new spec
ui.input_action_button("jumble", "Random fill color")


@reactive.effect
@reactive.event(input.jumble)
def _():
    import random

    color = random.choice(["#e45756", "#72b7b2", "#54a24b", "#f2cf5b"])
    plot.widget.spec = {
        "grid": True,
        "marks": [
            Plot.dot(
                penguins,
                {"x": "flipper_length_mm", "y": "body_mass_g", "fill": color},
            )
        ],
    }
