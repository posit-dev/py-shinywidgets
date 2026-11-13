# Title: Draw-a-dataset model explorer
# One-line: One canvas, three ML tasks -- classification, regression, and
#     clustering -- each refit live as you draw, for building intuition
#     about how models respond to the data you give them.
# Bucket: showcase
# Run: uv run --with scikit-learn shiny run docs/widget-guides/drawdata/gallery/showcase_model_explorer.py
# Data: none -- you draw it.

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
from drawdata import ScatterWidget
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_altair, render_drawdata
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import PolynomialFeatures

W, H = 800, 400

ui.page_opts(title="Draw-a-dataset model explorer", fillable=True)

with ui.sidebar(open="desktop", width=260):
    ui.input_radio_buttons(
        "task",
        "What should Python learn from your drawing?",
        {
            "classify": "Classification (2 classes)",
            "regress": "Regression (1 class = trend)",
            "cluster": "Clustering (unlabeled)",
        },
    )
    ui.input_action_button("clear", "Clear canvas", class_="btn-outline-secondary mt-2")

    @render.ui
    def task_help():
        return {
            "classify": ui.markdown(
                "Pick class **a**, drag some points, pick class **b**, drag "
                "more. The right panel shows a logistic-regression decision "
                "boundary between them."
            ),
            "regress": ui.markdown(
                "Draw a single-color trend left to right. The right panel "
                "fits a degree-2 polynomial through it."
            ),
            "cluster": ui.markdown(
                "Draw a few loose, separated blobs (still single-color -- "
                "clustering doesn't use the class labels). The right panel "
                "runs k-means and colors points by assigned cluster."
            ),
        }[input.task()]


# n_classes is read once at construction, so the canvas re-renders (losing
# its drawing) whenever the task changes between "classify" (2) and the
# others (1) -- that's the right tradeoff here, since the two modes expect
# different kinds of drawings.
@render_drawdata
def canvas():
    input.clear()  # also re-render (and clear) on the Clear button
    n = 2 if input.task() == "classify" else 1
    return ScatterWidget(width=W, height=H, n_classes=n)


@reactive.calc
def drawn() -> pd.DataFrame:
    return pd.DataFrame(canvas.read("data"))


@render_altair
def model_view():
    df = drawn()
    base_axes = dict(
        x=alt.X("x:Q", scale=alt.Scale(domain=[0, W]), title=None),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[0, H]), title=None),
    )
    task = input.task()

    if task == "classify":
        if df.empty or df["label"].nunique() < 2:
            return (
                alt.Chart(pd.DataFrame({"x": [], "y": []}))
                .mark_point()
                .encode(**base_axes)
            )
        X, y = df[["x", "y"]].to_numpy(), df["label"].to_numpy()
        clf = KNeighborsClassifier(n_neighbors=min(5, len(X))).fit(X, y)
        gx, gy = np.meshgrid(np.linspace(0, W, 50), np.linspace(0, H, 25))
        grid = pd.DataFrame({"x": gx.ravel(), "y": gy.ravel()})
        grid["pred"] = clf.predict(grid[["x", "y"]])
        field = (
            alt.Chart(grid)
            .mark_square(size=180, opacity=0.25)
            .encode(color=alt.Color("pred:N", legend=None), **base_axes)
        )
        points = (
            alt.Chart(df)
            .mark_point(filled=True, size=70)
            .encode(
                color=alt.Color("label:N", legend=alt.Legend(title=None)), **base_axes
            )
        )
        return field + points

    if task == "regress":
        if len(df) < 3:
            return (
                alt.Chart(pd.DataFrame({"x": [], "y": []}))
                .mark_point()
                .encode(**base_axes)
            )
        poly = PolynomialFeatures(degree=2).fit_transform(df[["x"]])
        coefs = np.linalg.lstsq(poly, df["y"], rcond=None)[0]
        xs = np.linspace(df["x"].min(), df["x"].max(), 100)
        fit = pd.DataFrame({"x": xs})
        fit["y"] = PolynomialFeatures(degree=2).fit_transform(fit[["x"]]) @ coefs
        points = alt.Chart(df).mark_point(filled=True).encode(**base_axes)
        line = alt.Chart(fit).mark_line(color="#d62728", size=3).encode(**base_axes)
        return points + line

    # cluster
    if len(df) < 2:
        return (
            alt.Chart(pd.DataFrame({"x": [], "y": []})).mark_point().encode(**base_axes)
        )
    k = min(3, len(df))
    labels = KMeans(n_clusters=k, n_init=5, random_state=0).fit_predict(df[["x", "y"]])
    df = df.assign(cluster=[str(c) for c in labels])
    return (
        alt.Chart(df)
        .mark_point(filled=True, size=70)
        .encode(color=alt.Color("cluster:N", legend=None), **base_axes)
    )


@render.text
def logistic_note():
    if input.task() != "classify" or drawn().empty or drawn()["label"].nunique() < 2:
        return ""
    # A from-scratch logistic-regression fit, just to report its accuracy
    # alongside the k-NN boundary plotted above.
    df = drawn()
    X, y = df[["x", "y"]].to_numpy(), (df["label"] == df["label"].iloc[0]).astype(int)
    if y.nunique() < 2:
        return ""
    acc = LogisticRegression().fit(X, y).score(X, y)
    return f"(a straight-line logistic fit gets {acc:.0%} training accuracy on this drawing)"
