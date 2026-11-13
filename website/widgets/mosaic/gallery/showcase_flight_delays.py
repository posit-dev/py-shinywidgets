# Title: 2 million flights, crossfiltered live
# Description: 2 million rows, crossfiltered live: a raster plot, a
#   histogram, and a carrier toggle. Demonstrates that Mosaic's
#   query-per-brush approach keeps scale off the browser's plate: value
#   boxes and a per-carrier table are computed in DuckDB from the selection.
# Bucket: showcase
# Run: uv run --no-sync shiny run docs/widget-guides/mosaic/gallery/showcase_flight_delays.py
# Data: synthesized in-process (numpy); a real dataset this large and this
#   shape isn't readily available as a small download

from __future__ import annotations

import numpy as np
import pandas as pd
from mosaic_widget import MosaicWidget
from shiny import reactive
from shiny.express import render, ui
# shiny.express.ui's layout_columns()/value_box() are context managers, meant
# for direct use in the page body -- inside a @render.ui function (below) you
# need the plain shiny.ui versions, which return a value instead.
from shiny.ui import layout_columns, value_box
from shinywidgets import render_mosaic_widget

rng = np.random.default_rng(0)
N = 2_000_000
CARRIERS = ["AA", "DL", "UA", "WN", "B6"]

carrier = rng.choice(CARRIERS, size=N, p=[0.28, 0.24, 0.22, 0.18, 0.08])
hour = rng.uniform(0, 24, N)
carrier_bias = pd.Series(carrier).map(dict(zip(CARRIERS, [0, -2, 3, -4, 5]))).to_numpy()
evening_bias = np.where(hour > 16, (hour - 16) * 2.2, 0)
delay = np.clip(rng.gamma(2.0, 7.0, N) - 9 + carrier_bias + evening_bias, -25, 180)

flights = pd.DataFrame({"carrier": carrier, "hour": hour, "delay": delay})

SPEC = {
    "params": {
        "brush": {"select": "intersect"},
        "carrier": {"select": "intersect"},
    },
    "vconcat": [
        {
            "plot": [
                {
                    "mark": "raster",
                    "data": {"from": "flights", "filterBy": "$carrier"},
                    "x": "hour",
                    "y": "delay",
                    "fill": "density",
                },
                {"select": "intervalXY", "as": "$brush"},
            ],
            "xDomain": [0, 24],
            "yDomain": [-25, 180],
            "colorScale": "symlog",
            "colorScheme": "turbo",
            "xLabel": "Hour of day (UTC)",
            "yLabel": "Delay (minutes)",
            "width": 620,
            "height": 280,
        },
        {
            "hconcat": [
                {
                    "plot": [
                        {
                            "mark": "rectY",
                            "data": {"from": "flights", "filterBy": "$carrier"},
                            "x": {"bin": "delay"},
                            "y": {"count": ""},
                            "fill": "#555",
                            "inset": 0.5,
                        },
                        {
                            "mark": "rectY",
                            "data": {"from": "flights", "filterBy": "$brush"},
                            "x": {"bin": "delay"},
                            "y": {"count": ""},
                            "fill": "#f4a259",
                            "inset": 0.5,
                        },
                    ],
                    "xDomain": [-25, 180],
                    "xLabel": "Delay (minutes)",
                    "width": 380,
                    "height": 180,
                },
                {
                    "plot": [
                        {
                            "mark": "barX",
                            "data": {"from": "flights", "filterBy": "$brush"},
                            "x": {"count": ""},
                            "y": "carrier",
                            "fill": "#f4a259",
                            "sort": {"y": "-x"},
                        },
                        {"select": "toggleY", "as": "$carrier"},
                    ],
                    "yLabel": None,
                    "width": 220,
                    "height": 180,
                },
            ]
        },
    ],
}

ui.page_opts(title="2M flights, crossfiltered", fillable=True)
ui.input_dark_mode(mode="dark")

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Brush the raster or histogram; click a carrier bar to isolate it")

        @render_mosaic_widget
        def dashboard():
            return MosaicWidget(SPEC, data={"flights": flights})

    with ui.card():
        ui.card_header("Selection, computed in DuckDB")

        @reactive.calc
        def selected():
            # table= omitted (one source table); filters by every active
            # selection ("brush" and "carrier") by default
            dashboard.params()
            return dashboard.data()

        @render.ui
        def stats():
            n, pct_on_time, avg_delay = selected().aggregate(
                "count(*), 100.0 * avg((delay <= 0)::INT), avg(delay)"
            ).fetchall()[0]
            share = 100 * n / N
            return layout_columns(
                value_box(f"{n:,}", f"flights ({share:.1f}%)", theme="primary"),
                value_box(f"{pct_on_time:.0f}%", "on time", theme="success"),
                value_box(f"{avg_delay:.1f} min", "average delay", theme="secondary"),
                col_widths=12,
            )

        @render.data_frame
        def by_carrier():
            cols = "carrier, count(*) AS n, round(avg(delay), 1) AS avg_delay"
            df = selected().aggregate(cols, "carrier").order("n DESC").df()
            return render.DataGrid(df)
