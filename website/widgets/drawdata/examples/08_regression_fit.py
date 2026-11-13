from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from drawdata import ScatterWidget
from shiny.express import ui
from shinywidgets import render_drawdata, render_matplotlib

W, H = 800, 400  # the widget's coordinate space (y points up)

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        ui.card_header("Draw a trend (single class = regression mode)")

        @render_drawdata
        def canvas():
            return ScatterWidget(width=W, height=H, n_classes=1)

    with ui.card(full_screen=True):
        ui.card_header("Quadratic fit, refit on every stroke")

        @render_matplotlib
        def fit():
            # A dependency on "data" also covers data_as_X_y, computed from
            # the same trait; with one color drawn, it returns (X, y) for
            # regression instead of (X, hex colors) for classification.
            canvas.read("data")
            X, y = canvas.widget.data_as_X_y

            fig, ax = plt.subplots(figsize=(5, 2.5))
            ax.set_xlim(0, W)
            ax.set_ylim(0, H)
            if len(X) < 3:
                ax.text(
                    W / 2, H / 2, "draw at least 3 points", ha="center", color="grey"
                )
                return fig
            x = X.ravel()
            coeffs = np.polyfit(x, y, deg=2)
            xs = np.linspace(x.min(), x.max(), 100)
            ax.scatter(x, y, s=12, color="#1f77b4")
            ax.plot(xs, np.polyval(coeffs, xs), color="#d62728", linewidth=2)
            return fig
