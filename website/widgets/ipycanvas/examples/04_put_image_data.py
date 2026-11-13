import numpy as np
import plotly.express as px
from ipycanvas import Canvas
from shiny.express import ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="put_image_data", fillable=True)

COLS = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
corr = px.data.iris()[COLS].corr().to_numpy()

CELL = 70  # pixels per correlation-matrix cell


def corr_to_rgba(corr: np.ndarray, cell: int) -> np.ndarray:
    # Diverging colormap: blue (-1) - white (0) - red (+1), each cell a solid
    # block of `cell` x `cell` pixels (an (h, w, 4) uint8 RGBA buffer)
    t = (corr + 1) / 2  # 0..1
    r = np.where(t > 0.5, 255, (255 * (2 * t)).astype(np.uint8))
    b = np.where(t < 0.5, 255, (255 * (2 * (1 - t))).astype(np.uint8))
    g = 255 - np.abs(255 - r.astype(int) - (255 - b.astype(int)))
    rgba = np.stack([r, g, b, np.full_like(r, 255)], axis=-1).astype(np.uint8)
    return np.kron(rgba, np.ones((cell, cell, 1), dtype=np.uint8))


with ui.card(full_screen=True):

    @render_ipycanvas
    def heatmap():
        n = len(COLS)
        c = Canvas(width=n * CELL, height=n * CELL)
        c.put_image_data(corr_to_rgba(corr, CELL), 0, 0)

        c.font = "13px sans-serif"
        c.text_align = "center"
        for i in range(n):
            for j in range(n):
                c.fill_style = "#000" if abs(corr[i, j]) < 0.6 else "#fff"
                x, y = j * CELL + CELL / 2, i * CELL + CELL / 2
                c.fill_text(f"{corr[i, j]:.2f}", x, y + 4)
        return c
