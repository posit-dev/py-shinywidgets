# Brushing large data: push summaries, not points. A datashader raster over
# 5M Gaia stars; box-selecting either histogram (brushing(), the live,
# debounced variant of brushed()) re-filters a shared param.Parameterized
# state the raster's DynamicMap watches -- re-rasterizing in place -- and
# writes the OTHER histogram's bar heights in place. Every brush step ships
# one image plus two arrays of 50 numbers, not the 5,000,000 rows.
from __future__ import annotations

import os
from pathlib import Path

import holoviews as hv
import numpy as np
import pandas as pd
import param
import plotly.graph_objects as go
from holoviews.operation.datashader import rasterize
from holoviews.streams import Params
from shiny import reactive
from shiny.express import ui

from shinywidgets import render_holoviews, render_plotly

hv.extension("bokeh")

DATA_PATH = Path(__file__).parent.parent / "data" / "gaia-5m.parquet"
gaia = pd.read_parquet(DATA_PATH, columns=["l", "b", "parallax", "phot_g_mean_mag"])
# measure/brush_payload.py overrides this to re-run the app at a smaller scale.
_n_rows = int(os.environ.get("LINKED_VIEWS_ROWS", len(gaia)))
if _n_rows < len(gaia):
    gaia = gaia.sample(n=_n_rows, random_state=0).reset_index(drop=True)

# Fixed bin edges so a brush only ever changes bar HEIGHTS, never the bins.
MAG_BINS = np.linspace(14.0, 21.5, 51)
PLX_BINS = np.linspace(-3.0, 5.0, 51)
MAG_CENTERS = (MAG_BINS[:-1] + MAG_BINS[1:]) / 2
PLX_CENTERS = (PLX_BINS[:-1] + PLX_BINS[1:]) / 2


def mag_counts(df: pd.DataFrame) -> np.ndarray:
    counts, _ = np.histogram(df["phot_g_mean_mag"].dropna(), bins=MAG_BINS)
    return counts


def plx_counts(df: pd.DataFrame) -> np.ndarray:
    counts, _ = np.histogram(df["parallax"].dropna(), bins=PLX_BINS)
    return counts


class BrushState(param.Parameterized):
    # (column, lo, hi) of the active brush, or None. One brush at a time --
    # brushing a new histogram replaces whichever filter was active before.
    filter_range = param.Parameter(default=None)


state = BrushState()  # one per session (Express re-runs this module per session)


def filtered(df: pd.DataFrame) -> pd.DataFrame:
    fr = state.filter_range
    if fr is None:
        return df
    col, lo, hi = fr
    return df[df[col].between(lo, hi)]


def make_points(filter_range):
    return hv.Points(filtered(gaia), ["l", "b"])


ui.page_opts(title="Brushing large data: push summaries, not points", fillable=True)

with ui.card(full_screen=True):
    ui.card_header(f"Sky map: {len(gaia):,} Gaia stars, rasterized")

    @render_holoviews
    def sky():
        points_dmap = hv.DynamicMap(make_points, streams=[Params(state, ["filter_range"])])
        return rasterize(points_dmap).opts(
            responsive=True,
            cmap="fire",
            cnorm="eq_hist",
            colorbar=True,
            xlim=(0, 360),
            ylim=(-90, 90),
        )


with ui.layout_columns(col_widths=[6, 6]):
    with ui.card():
        ui.card_header("Magnitude (brush to filter)")

        @render_plotly
        def mag_hist():
            fig = go.Figure(go.Bar(x=MAG_CENTERS, y=mag_counts(gaia), marker_color="#4c78a8"))
            fig.update_layout(dragmode="select", height=260, margin=dict(l=40, r=10, t=10, b=30))
            return fig

    with ui.card():
        ui.card_header("Parallax (brush to filter)")

        @render_plotly
        def plx_hist():
            fig = go.Figure(go.Bar(x=PLX_CENTERS, y=plx_counts(gaia), marker_color="#f58518"))
            fig.update_layout(dragmode="select", height=260, margin=dict(l=40, r=10, t=10, b=30))
            return fig


@reactive.effect
def _brush_magnitude():
    region = mag_hist.brushing()
    if region is None:
        return
    lo, hi = region["range"]["x"]
    with reactive.isolate():
        state.filter_range = ("phot_g_mean_mag", lo, hi)
        sub = gaia[gaia["phot_g_mean_mag"].between(lo, hi)]
        with plx_hist.widget.batch_update():
            plx_hist.widget.data[0].y = plx_counts(sub)


@reactive.effect
def _brush_parallax():
    region = plx_hist.brushing()
    if region is None:
        return
    lo, hi = region["range"]["x"]
    with reactive.isolate():
        state.filter_range = ("parallax", lo, hi)
        sub = gaia[gaia["parallax"].between(lo, hi)]
        with mag_hist.widget.batch_update():
            mag_hist.widget.data[0].y = mag_counts(sub)
