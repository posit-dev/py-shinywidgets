from __future__ import annotations

import numpy as np
import pandas as pd
from mosaic_widget import MosaicWidget
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_mosaic_widget

rng = np.random.default_rng(1)
n = 2000
species = rng.choice(["Adelie", "Chinstrap", "Gentoo"], size=n)
offset = pd.Series(species).map({"Adelie": 0, "Chinstrap": 1, "Gentoo": 2}).to_numpy()
penguins = pd.DataFrame(
    {
        "species": species,
        "flipper_length": rng.normal(185 + 12 * offset, 6),
        "body_mass": rng.normal(3500 + 700 * offset, 250),
    }
)

# Every plot reads from the "penguins" table through the shared `brush`
# selection, so brushing one plot filters the others (a "crossfilter").
spec = {
    "params": {"brush": {"select": "crossfilter"}},
    "vconcat": [
        {
            "plot": [
                {
                    "mark": "dot",
                    "data": {"from": "penguins", "filterBy": "$brush"},
                    "x": "flipper_length",
                    "y": "body_mass",
                    "fill": "species",
                    "r": 2.5,
                },
                {"select": "intervalXY", "as": "$brush"},
            ],
            "xDomain": "Fixed",
            "yDomain": "Fixed",
            "width": 600,
            "height": 300,
        },
        {
            "plot": [
                {
                    "mark": "rectY",
                    "data": {"from": "penguins", "filterBy": "$brush"},
                    "x": {"bin": "flipper_length"},
                    "y": {"count": ""},
                    "fill": "steelblue",
                    "inset": 0.5,
                },
                {"select": "intervalX", "as": "$brush"},
            ],
            "xDomain": "Fixed",
            "width": 600,
            "height": 150,
        },
    ],
}

app_ui = ui.page_fillable(
    ui.layout_columns(
        ui.card(
            ui.card_header("Brush either plot to cross-filter"),
            output_widget("dashboard"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Selected penguins, in Python"),
            ui.output_text("n_selected"),
            ui.output_data_frame("summary"),
        ),
        col_widths=[8, 4],
    ),
)


def server(input, output, session):
    @render_mosaic_widget
    def dashboard():
        return MosaicWidget(spec, data={"penguins": penguins})

    @reactive.calc
    def selected():
        # The widget's `params` trait changes whenever a brush changes
        reactive_read(dashboard.widget, "params")
        # A lazy DuckDB relation: aggregate it in DuckDB rather than pulling every
        # selected row into pandas
        return dashboard.widget.data()

    @render.text
    def n_selected():
        (n,) = selected().aggregate("count(*)").fetchall()[0]
        return f"{n} of {len(penguins)} penguins selected"

    @render.data_frame
    def summary():
        return render.DataGrid(
            selected()
            .aggregate(
                "species, count(*) AS n, round(avg(body_mass)) AS mean_mass",
                "species",
            )
            .order("species")
            .df()
        )


app = App(app_ui, server)
