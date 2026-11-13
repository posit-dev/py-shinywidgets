from __future__ import annotations

import polars as pl
from pyobsplot import Plot
from shiny.express import ui

from shinywidgets import render_obsplot

ui.page_opts(title="tip: a rich hover card, not just an (x, y)", fillable=True)

penguins = pl.read_csv(
    "https://github.com/juba/pyobsplot/raw/main/doc/data/penguins.csv"
)

with ui.card(full_screen=True):
    ui.card_header("Hover a point for full detail")

    @render_obsplot
    def tipped():
        return Plot.plot(
            {
                "color": {"legend": True},
                "marks": [
                    Plot.dot(
                        penguins,
                        {
                            "x": "flipper_length_mm",
                            "y": "body_mass_g",
                            "fill": "species",
                        },
                    ),
                    # tip + pointer: find the nearest point and show a
                    # custom set of fields, not just the plotted channels.
                    Plot.tip(
                        penguins,
                        Plot.pointer(
                            {
                                "x": "flipper_length_mm",
                                "y": "body_mass_g",
                                "channels": {
                                    "Species": "species",
                                    "Island": "island",
                                    "Sex": "sex",
                                },
                            }
                        ),
                    ),
                ],
            }
        )
