from __future__ import annotations

import polars as pl
from pyobsplot import Plot
from shiny.express import ui

from shinywidgets import render_obsplot

ui.page_opts(title="Observable Plot quickstart", fillable=True)

penguins = pl.read_csv(
    "https://github.com/juba/pyobsplot/raw/main/doc/data/penguins.csv"
)

with ui.card(full_screen=True):
    ui.card_header("Palmer penguins")

    @render_obsplot
    def plot():
        return Plot.plot(
            {
                "grid": True,
                "color": {"legend": True},
                "marks": [
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
            }
        )
