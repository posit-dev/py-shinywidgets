# Draw a dataset, watch Python learn it.
#
# Draw points of two (or more) classes on the canvas with the brush; a k-NN
# classifier trained on your drawing is re-fit on every stroke and its
# decision boundary is rendered beside the canvas.
#
# Note: the widget only syncs a drawing batch to Python once the *next* batch
# starts (upstream drawdata issue #40), so the boundary updates one stroke
# behind your drawing. Undo and reset sync immediately.

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from drawdata import ScatterWidget
from shiny import render
from shiny.express import ui

from shinywidgets import reactive_read, render_drawdata

W, H = 800, 400  # the widget's coordinate space (y points up in the data)


def drawn() -> pd.DataFrame:
    # NOTE: a plain `canvas.widget.data` (or `.data_as_pandas`) read is not
    # reactive -- always go through reactive_read() to re-run on new strokes.
    return pd.DataFrame(reactive_read(canvas.widget, "data"))


with ui.layout_columns(col_widths=(7, 5)):
    with ui.card():
        ui.card_header("Draw a dataset (pick a class, then drag the brush)")

        @render_drawdata
        def canvas():
            return ScatterWidget(width=W, height=H, n_classes=2)

    with ui.card():
        ui.card_header("Python learns your drawing (k-NN, k=5)")

        @render.plot
        def boundary():
            df = drawn()
            fig, ax = plt.subplots(figsize=(5, 4.6))
            ax.set_xlim(0, W)
            ax.set_ylim(0, H)
            if df.empty or df["label"].nunique() < 2:
                ax.text(
                    W / 2,
                    H / 2,
                    "draw points of both classes",
                    ha="center",
                    va="center",
                    color="grey",
                )
                return fig
            X = df[["x", "y"]].to_numpy()
            y = df["label"].to_numpy()
            classes, y_idx = np.unique(y, return_inverse=True)
            # k-NN decision boundary over a coarse grid
            gx, gy = np.meshgrid(np.linspace(0, W, 100), np.linspace(0, H, 50))
            grid = np.c_[gx.ravel(), gy.ravel()]
            d2 = ((grid[:, None, :] - X[None, :, :]) ** 2).sum(-1)
            knn = np.argsort(d2, axis=1)[:, :5]
            votes = np.apply_along_axis(
                lambda r: np.bincount(r).argmax(), 1, y_idx[knn]
            )
            ax.contourf(gx, gy, votes.reshape(gx.shape), levels=len(classes), alpha=0.25)
            for c, name in zip(["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"], classes):
                pts = X[y == name]
                ax.scatter(pts[:, 0], pts[:, 1], c=c, s=12, label=name)
            ax.legend(loc="upper right")
            return fig


@render.code
def summary():
    df = drawn()
    if df.empty:
        return "No data yet — draw something!"
    return (
        f"{len(df)} points drawn\n"
        + df.groupby("label").size().to_string()
        + "\n\nHead:\n"
        + df.head(3).to_string(index=False)
    )
