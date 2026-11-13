# Needs scikit-learn: uv run --with scikit-learn shiny run
#   docs/widget-guides/drawdata/examples/07_classifier_boundary.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from drawdata import ScatterWidget
from shiny.express import ui
from shinywidgets import render_drawdata, render_plotly
from sklearn.neighbors import KNeighborsClassifier

W, H = 800, 400  # the widget's coordinate space (y points up)

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        ui.card_header("Draw two classes")

        @render_drawdata
        def canvas():
            return ScatterWidget(width=W, height=H, n_classes=2)

    with ui.card(full_screen=True):
        ui.card_header("k-NN decision boundary, refit on every stroke")

        @render_plotly
        def boundary():
            df = pd.DataFrame(canvas.read("data"))
            fig = go.Figure()
            fig.update_xaxes(range=[0, W], visible=False)
            fig.update_yaxes(range=[0, H], visible=False, scaleanchor="x")
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
            if df.empty or df["label"].nunique() < 2:
                fig.add_annotation(
                    text="draw points of both classes",
                    x=W / 2,
                    y=H / 2,
                    showarrow=False,
                )
                return fig

            X = df[["x", "y"]].to_numpy()
            y = df["label"].to_numpy()
            clf = KNeighborsClassifier(n_neighbors=min(5, len(X))).fit(X, y)

            gx, gy = np.meshgrid(np.linspace(0, W, 120), np.linspace(0, H, 60))
            grid = np.c_[gx.ravel(), gy.ravel()]
            _, pred_idx = np.unique(clf.predict(grid), return_inverse=True)
            fig.add_contour(
                x=gx[0],
                y=gy[:, 0],
                z=pred_idx.reshape(gx.shape),
                showscale=False,
                opacity=0.35,
                colorscale="Portland",
            )
            for label, group in df.groupby("label"):
                fig.add_scatter(
                    x=group["x"],
                    y=group["y"],
                    mode="markers",
                    marker=dict(color=group["color"].iloc[0], size=8),
                    name=label,
                )
            return fig
