import duckdb
import numpy as np
import pandas as pd
import pygwalker
from shiny import App, ui
from shinywidgets import output_widget, render_pygwalker

# PyGWalker otherwise sends usage events and checks for updates, from both the
# Python process and each visitor's browser
pygwalker.GlobalVarManager.set_privacy("offline")

# PyGWalker computes charts by running SQL that the browser sends on DuckDB's
# default connection, so any visitor could otherwise read and write files on the
# server. render_pygwalker requires that connection to be locked down before it
# renders (TimeZone first: PyGWalker sets it per query, and can't once the
# configuration is locked).
duckdb.execute("SET TimeZone = 'UTC'")
duckdb.execute("SET enable_external_access = false")
duckdb.execute("SET lock_configuration = true")

rng = np.random.default_rng(1)

cars = pd.DataFrame(
    {
        "model": [f"Car {i + 1}" for i in range(500)],
        "origin": rng.choice(["USA", "Europe", "Japan"], 500),
        "weight": rng.uniform(1.5, 5.0, 500).round(2),
    }
)
cars["mpg"] = (45 - 6 * cars["weight"] + rng.normal(0, 2.5, 500)).round(1)
cars["hp"] = (40 * cars["weight"] + rng.normal(0, 25, 500)).round()

days = pd.date_range("2023-01-01", periods=2 * 365, freq="D")
sales = pd.DataFrame(
    {
        "date": days,
        "region": rng.choice(["North", "South", "East", "West"], len(days)),
        "units": rng.poisson(40, len(days)),
    }
)
sales["revenue"] = (sales["units"] * rng.uniform(8, 12, len(days))).round(2)

DATASETS = {"cars": cars, "sales": sales}

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_radio_buttons(
                "dataset", "Dataset", choices=list(DATASETS), selected="cars"
            ),
            ui.p(
                "Drag fields onto the axes to build charts. Switching datasets "
                "re-renders the explorer.",
                class_="text-muted small",
            ),
        ),
        ui.card(
            ui.card_header("Explore the data"),
            output_widget("explorer"),
            full_screen=True,
        ),
    ),
    title="PyGWalker",
)


def server(input, output, session):
    @render_pygwalker
    def explorer():
        return DATASETS[input.dataset()]


app = App(app_ui, server)
