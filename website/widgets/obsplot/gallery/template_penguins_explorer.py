# Observable Plot: penguin view switcher (template)
# A small, adaptable starting point: a select input rebuilds the plot spec,
# and a button updates the fill color in place without a re-render.
# Bucket: template. Run: shiny run template_penguins_explorer.py
# Data: pyobsplot's bundled Palmer penguins CSV (juba/pyobsplot on GitHub).

from __future__ import annotations

import random

import polars as pl
from pyobsplot import Plot
from shiny import reactive
from shiny.express import input, ui

from shinywidgets import render_obsplot

ui.page_opts(title="Palmer penguins, Observable Plot style", fillable=True)

penguins = pl.read_csv(
    "https://github.com/juba/pyobsplot/raw/main/doc/data/penguins.csv"
)

ACCENTS = ["#4e79a7", "#e15759", "#59a14f", "#edc948"]

VIEWS = {
    "Scatter": lambda: [
        Plot.dot(
            penguins,
            {"x": "flipper_length_mm", "y": "body_mass_g", "fill": "species"},
        ),
    ],
    "Scatter + tip": lambda: [
        Plot.dot(
            penguins,
            {
                "x": "flipper_length_mm",
                "y": "body_mass_g",
                "fill": "species",
                "tip": True,
            },
        ),
    ],
    "Density contours": lambda: [
        Plot.density(
            penguins,
            {"x": "flipper_length_mm", "y": "body_mass_g", "stroke": "species"},
        ),
    ],
    "Beeswarm by species": lambda: [
        Plot.dotX(
            penguins,
            Plot.dodgeY({"x": "body_mass_g", "fill": "species", "r": 3}),
        ),
    ],
}

with ui.card(full_screen=True):
    ui.card_header("Palmer penguins")
    ui.input_select("view", "View", choices=list(VIEWS))

    @render_obsplot
    def plot():
        return Plot.plot(
            {
                "grid": True,
                "color": {"legend": True},
                "marks": VIEWS[input.view()](),
            }
        )


ui.input_action_button("accent", "Shuffle accent color (in place)")


@reactive.effect
@reactive.event(input.accent)
def _():
    # No re-render: assigning .widget.spec redraws the same chart instance.
    color = random.choice(ACCENTS)
    plot.widget.spec = {
        "grid": True,
        "marks": [
            Plot.dot(
                penguins,
                {"x": "flipper_length_mm", "y": "body_mass_g", "fill": color},
            ),
        ],
    }
