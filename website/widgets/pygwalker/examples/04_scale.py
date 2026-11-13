import numpy as np
import pandas as pd
from shiny.express import ui

import globals  # noqa: F401 -- locks down DuckDB once per process; see globals.py
from shinywidgets import render_pygwalker

ui.page_opts(fillable=True)
ui.markdown(
    "1,000,000 synthetic rows. PyGWalker aggregates with DuckDB in the Python "
    "process, so only the query *result* crosses the wire -- opening the explorer "
    "and building a chart here cost the same bytes and time as "
    "02_build_a_chart.py's 244 rows (measured in NOTES.md)."
)

rng = np.random.default_rng(0)
n = 1_000_000
trips = pd.DataFrame(
    {
        "fare": rng.gamma(4, 3, n).round(2),
        "distance_mi": rng.gamma(3, 1.5, n).round(2),
        "borough": rng.choice(
            ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"],
            n,
            p=[0.45, 0.25, 0.2, 0.07, 0.03],
        ),
        "payment": rng.choice(["card", "cash"], n, p=[0.7, 0.3]),
    }
)


@render_pygwalker
def explorer():
    return trips
