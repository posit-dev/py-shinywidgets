# Title: Classifier playground
# One-line: Draw two classes by hand and watch a k-NN decision boundary
#     refit live, next to a point count and a clear button.
# Bucket: template
# Run: uv run --with scikit-learn shiny run docs/widget-guides/drawdata/gallery/template_classifier_playground.py
# Data: none -- you draw it.
#
# Adapt this by swapping KNeighborsClassifier for any other sklearn
# classifier (LogisticRegression, SVC, a small MLP, ...), or ScatterWidget's
# n_classes for more groups.

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from drawdata import ScatterWidget
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_drawdata, render_plotly
from sklearn.neighbors import KNeighborsClassifier

W, H = 800, 400

ui.page_opts(title="Classifier playground", fillable=True)

with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        with ui.card_header(class_="d-flex justify-content-between align-items-center"):
            "Draw two classes"
            ui.input_action_button(
                "clear", "Clear", class_="btn-sm btn-outline-secondary"
            )

        @render_drawdata
        def canvas():
            return ScatterWidget(width=W, height=H, n_classes=2)

    with ui.card(full_screen=True):
        with ui.card_header(class_="d-flex justify-content-between align-items-center"):
            "k-NN decision boundary"
            ui.input_slider("k", "neighbors (k)", min=1, max=15, value=5, width="200px")

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

            X, y = df[["x", "y"]].to_numpy(), df["label"].to_numpy()
            k = min(input.k(), len(X))
            clf = KNeighborsClassifier(n_neighbors=k).fit(X, y)
            gx, gy = np.meshgrid(np.linspace(0, W, 120), np.linspace(0, H, 60))
            _, pred_idx = np.unique(
                clf.predict(np.c_[gx.ravel(), gy.ravel()]), return_inverse=True
            )
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


@render.text
def status():
    n = len(canvas.read("data"))
    return f"{n} points drawn"


@reactive.effect
@reactive.event(input.clear)
def _clear():
    canvas.widget.data = []
