# quak showcase: a multi-million-row trip explorer
# Brushing quak's histograms (or clicking a borough bar) filters a table of
# several million synthetic taxi-style rides, and every other panel -- value
# boxes, a plotly chart, and a CSV download -- updates to describe exactly
# the filtered rows, computed in DuckDB without copying the data out of
# Python.
# bucket: showcase
# run: uv run --no-sync shiny run docs/widget-guides/quak/gallery/showcase_trip_explorer.py
# data: synthetic (sized for scale; see generate_rides() below)

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
from shiny import render
from shiny.express import ui
from shinywidgets import render_plotly, render_quak

ui.page_opts(title="Trip explorer", fillable=True)


def generate_rides(n: int = 3_000_000) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    borough = rng.choice(boroughs, n, p=[0.45, 0.25, 0.2, 0.07, 0.03])
    # Commuter peaks at 8 and 18; Manhattan trips run a bit shorter
    hour = (rng.normal(13, 5, n) + rng.normal(0, 1, n) * (rng.random(n) < 0.5)).astype(
        int
    ) % 24
    is_manhattan = borough == "Manhattan"
    trip_minutes = np.clip(
        rng.gamma(2.0, np.where(is_manhattan, 5.0, 7.5)), 1, 120
    ).round(1)
    fare_usd = np.clip(2.5 + trip_minutes * rng.uniform(0.8, 1.6, n), 2.5, 200).round(2)
    return pd.DataFrame(
        {"borough": borough, "hour": hour, "trip_minutes": trip_minutes, "fare_usd": fare_usd}
    )


rides = generate_rides()

with ui.layout_columns(col_widths=[8, 4], fill=False):
    ui.markdown(
        f"**{len(rides):,} synthetic rides.** Brush a histogram or click a "
        "borough bar below -- every panel on the right recomputes from "
        "exactly the filtered rows, via DuckDB, server-side."
    )

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Rides (filter by brushing a histogram or clicking a bar)")

        @render_quak
        def table():
            return rides

    with ui.layout_columns(col_widths=12, fill=False):
        with ui.value_box():
            "Rides selected"

            @render.text
            def n_rides():
                return f"{table.data().aggregate('count(*)').fetchall()[0][0]:,}"

        with ui.value_box():
            "Median fare"

            @render.text
            def median_fare():
                value = table.data().aggregate("median(fare_usd)").fetchall()[0][0]
                return f"${value:.2f}"

    with ui.card(full_screen=True):
        ui.card_header("Rides by hour, filtered")

        @render_plotly
        def by_hour():
            counts = (
                table.data()
                .aggregate("hour, count(*) as rides", "hour")
                .order("hour")
                .df()
            )
            fig = px.bar(counts, x="hour", y="rides")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            return fig

    with ui.card():
        ui.card_header("Export")
        "Download exactly the filtered rides as CSV."

        @render.download_button(filename="rides_filtered.csv", label="Download CSV")
        def download():
            yield table.data().df().to_csv(index=False)
