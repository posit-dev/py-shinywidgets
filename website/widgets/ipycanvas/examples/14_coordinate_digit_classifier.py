import io

import numpy as np
from ipycanvas import Canvas
from PIL import Image
from shiny.express import render, ui
from shinywidgets import render_ipycanvas
from sklearn.datasets import load_digits
from sklearn.svm import SVC

ui.page_opts(title="Draw a digit", fillable=True)

# scikit-learn's digits dataset: 1797 handwritten 0-9's as 8x8 grayscale
# images (pixel values 0-16). A tiny SVM trained on it classifies strokes
# drawn on the canvas, once they're downsampled to match.
digits = load_digits()
clf = SVC(gamma=0.001).fit(digits.data, digits.target)

SIZE = 196
drawing = {"last": None}

with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        ui.p("Draw a digit (0-9) with your mouse.")

        @render_ipycanvas
        def canvas():
            # sync_image_data=True makes the browser push the composited
            # bitmap back to Python -- read it with canvas.read("image_data").
            c = Canvas(width=SIZE, height=SIZE, sync_image_data=True)
            c.fill_style = "#000"
            c.fill_rect(0, 0, SIZE, SIZE)

            def on_down(x, y):
                drawing["last"] = (x, y)

            def on_move(x, y):
                if drawing["last"] is None:
                    return
                c.stroke_style = "#fff"
                c.line_width = 14
                c.line_cap = "round"
                c.stroke_line(*drawing["last"], x, y)
                drawing["last"] = (x, y)

            def on_up(x, y):
                drawing["last"] = None

            c.on_mouse_down(on_down)
            c.on_mouse_move(on_move)
            c.on_mouse_up(on_up)
            c.on_mouse_out(on_up)
            return c

    with ui.card():
        ui.card_header("Python's guess")

        @render.text
        def guess():
            png_bytes = canvas.read("image_data")
            if png_bytes is None:
                return "Draw something!"
            img = Image.open(io.BytesIO(png_bytes)).convert("L").resize((8, 8))
            pixels = np.asarray(img, dtype=float) / 255 * 16  # match 0-16 scale
            pred = clf.predict(pixels.reshape(1, -1))[0]
            return f"That looks like a {pred}"
