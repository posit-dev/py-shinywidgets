# Needs scikit-learn: uv run --with scikit-learn shiny run
#   docs/widget-guides/drawdata/examples/10_clustering.py
from __future__ import annotations

import altair as alt
import pandas as pd
from drawdata import ScatterWidget
from shiny.express import input, ui
from shinywidgets import render_altair, render_drawdata
from sklearn.cluster import KMeans

W, H = 800, 400

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        ui.card_header("Draw an unlabeled cloud of points")

        @render_drawdata
        def canvas():
            return ScatterWidget(width=W, height=H, n_classes=1)

    with ui.card(full_screen=True):
        with ui.card_header(class_="d-flex justify-content-between align-items-center"):
            "k-means clusters, refit on every stroke"
            ui.input_slider("k", None, min=2, max=5, value=3, width="160px")

        @render_altair
        def clusters():
            df = pd.DataFrame(canvas.read("data"))
            base = (
                alt.Chart()
                .mark_point()
                .encode(
                    x=alt.X("x:Q", scale=alt.Scale(domain=[0, W])),
                    y=alt.Y("y:Q", scale=alt.Scale(domain=[0, H])),
                )
            )
            if len(df) < input.k():
                return base
            labels = KMeans(n_clusters=input.k(), n_init=5, random_state=0).fit_predict(
                df[["x", "y"]]
            )
            df["cluster"] = [str(c) for c in labels]
            return (
                alt.Chart(df)
                .mark_point(filled=True, size=60)
                .encode(
                    x=alt.X("x:Q", scale=alt.Scale(domain=[0, W])),
                    y=alt.Y("y:Q", scale=alt.Scale(domain=[0, H])),
                    color=alt.Color("cluster:N", legend=None),
                )
            )
