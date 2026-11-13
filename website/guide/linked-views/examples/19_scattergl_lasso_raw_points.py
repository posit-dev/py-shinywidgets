# The anti-pattern: lassoing raw points at scale. Same Gaia data as 18, but
# sampled to 1M rows and plotted as individual go.Scattergl markers instead
# of a raster. The table reacts to selecting() -- the live variant of
# selected(), matching 18's brushing() -- so every point the lasso has
# caught so far streams back to Python continuously, and the work AND the
# payload grow with the SELECTION, not with a fixed image size like 18's.
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from shiny.express import ui

from shinywidgets import render_itables, render_plotly

DATA_PATH = Path(__file__).parent.parent / "data" / "gaia-5m.parquet"
# measure/brush_payload.py overrides this to re-run the app at a different scale.
SAMPLE_N = int(os.environ.get("LINKED_VIEWS_ROWS", "1000000"))

gaia = pd.read_parquet(DATA_PATH, columns=["l", "b", "phot_g_mean_mag"])
sample = gaia.sample(n=min(SAMPLE_N, len(gaia)), random_state=0).reset_index(drop=True)

ui.page_opts(title="Anti-pattern: lasso raw points at scale", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header(f"{SAMPLE_N:,} of {len(gaia):,} Gaia stars (Scattergl)")

        @render_plotly
        def scatter():
            fig = go.Figure(
                go.Scattergl(
                    x=sample["l"],
                    y=sample["b"],
                    mode="markers",
                    marker=dict(
                        size=2,
                        color=sample["phot_g_mean_mag"],
                        colorscale="Inferno",
                        opacity=0.5,
                    ),
                    customdata=sample.index,
                )
            )
            fig.update_layout(dragmode="lasso", xaxis_title="l", yaxis_title="b")
            return fig

    with ui.card(full_screen=True):
        ui.card_header("Lassoed stars")

        @render_itables
        def table():
            cols = ["l", "b", "phot_g_mean_mag"]
            pts = scatter.selecting()
            if pts is None or pts.empty:
                return sample.iloc[:0][cols]
            return sample.loc[sample.index.isin(pts["customdata"]), cols]
