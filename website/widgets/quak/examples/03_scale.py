from __future__ import annotations

import numpy as np
import pandas as pd
from shiny.express import ui
from shinywidgets import render_quak

ui.page_opts(title="quak at scale", fillable=True)

# Synthetic "ride" data, sized for scale rather than realism: quak only ever
# sends the rows on screen and each histogram's bin counts over the wire, so
# the browser payload is about the same at 5k rows or 5M.
n = 5_000_000
rng = np.random.default_rng(0)
rides = pd.DataFrame(
    {
        "borough": rng.choice(
            ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"],
            n,
            p=[0.45, 0.25, 0.2, 0.07, 0.03],
        ),
        "hour": rng.integers(0, 24, n),
        "trip_minutes": np.clip(rng.gamma(2.0, 6.0, n), 1, 120).round(1),
        "fare_usd": np.clip(rng.gamma(3.0, 5.0, n), 2.5, 200).round(2),
    }
)

with ui.card(full_screen=True):
    ui.card_header(f"{n:,} synthetic rides")

    @render_quak
    def table():
        return rides
