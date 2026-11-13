# Digit sketchpad: draw a digit and a small scikit-learn SVM (trained on
# sklearn's bundled load_digits dataset) classifies it live, with a
# confidence bar for its top-3 guesses. Shows off sync_image_data +
# canvas.read("image_data") as a bridge from raw canvas ink to a real ML model.
# bucket: showcase
# run: uv run --with scikit-learn shiny run showcase_digit_sketchpad.py
# data: sklearn.datasets.load_digits (bundled with scikit-learn)

import io

import numpy as np
from ipycanvas import Canvas
from PIL import Image
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipycanvas
from sklearn.calibration import CalibratedClassifierCV
from sklearn.datasets import load_digits
from sklearn.svm import SVC

ui.page_opts(title="Digit sketchpad", fillable=True)

digits = load_digits()
clf = CalibratedClassifierCV(SVC(gamma=0.001), ensemble=False).fit(
    digits.data, digits.target
)

SIZE = 224
drawn_count = reactive.value(0)


def classify(png_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(png_bytes)).convert("L").resize((8, 8))
    pixels = np.asarray(img, dtype=float) / 255 * 16  # match load_digits' 0-16 scale
    return clf.predict_proba(pixels.reshape(1, -1))[0]


def confidence_bar(digit: int, pct: float) -> ui.Tag:
    return ui.div(
        ui.span(str(digit), style="width: 1.5em; font-weight: bold; display: inline-block;"),
        ui.div(
            style=(
                f"width: {pct}%; max-width: 100%; background: #2c7fb8; height: 14px; "
                "display: inline-block; border-radius: 3px; vertical-align: middle;"
            )
        ),
        ui.span(f" {pct:.0f}%", style="margin-left: 6px; color: #555;"),
    )


with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        ui.card_header("Draw a digit (0-9)")
        ui.input_action_button("clear", "Clear", class_="mb-2")

        @render_ipycanvas
        def canvas():
            # sync_image_data=True makes the browser push the composited
            # bitmap back to Python -- read it with canvas.read("image_data").
            c = Canvas(width=SIZE, height=SIZE, sync_image_data=True)
            c.fill_style = "#000"
            c.fill_rect(0, 0, SIZE, SIZE)
            drawing = {"last": None}

            def on_down(x, y):
                drawing["last"] = (x, y)

            def on_move(x, y):
                if drawing["last"] is None:
                    return
                c.stroke_style = "#fff"
                c.line_width = 16
                c.line_cap = "round"
                c.stroke_line(*drawing["last"], x, y)
                drawing["last"] = (x, y)

            def on_up(x, y):
                if drawing["last"] is not None:
                    drawn_count.set(drawn_count() + 1)
                drawing["last"] = None

            c.on_mouse_down(on_down)
            c.on_mouse_move(on_move)
            c.on_mouse_up(on_up)
            c.on_mouse_out(on_up)
            return c

    with ui.card():
        ui.card_header("Prediction")

        @render.ui
        def prediction():
            png_bytes = canvas.read("image_data")
            if png_bytes is None or drawn_count() == 0:
                return ui.p("Draw something to see a prediction.")
            probs = classify(png_bytes)
            order = np.argsort(probs)[::-1][:3]
            bars = [confidence_bar(int(d), probs[d] * 100) for d in order]
            return ui.div(
                ui.h2(str(int(order[0])), style="margin: 0 0 10px 0;"),
                *bars,
                ui.p(
                    f"Digits drawn this session: {drawn_count()}",
                    style="margin-top: 14px; color: #777; font-size: 0.9em;",
                ),
            )


@reactive.effect
@reactive.event(input.clear)
def _():
    c = canvas.widget
    if c is not None:
        c.fill_style = "#000"
        c.fill_rect(0, 0, SIZE, SIZE)
