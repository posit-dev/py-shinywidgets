# title: Handwritten digits, with the average of your selection
# bucket: showcase
# description: 1,797 handwritten digits (sklearn's bundled digit images,
#   PCA-projected to 2D), each with an image thumbnail. Lasso or click-filter
#   a cluster and the sidebar reconstructs the *average* image of exactly
#   those digits from selected() -- a concrete payoff for "Python computes
#   on what the user circled," and it works through the bar/table crossfilter
#   even without a WebGPU-capable browser for the lasso itself.
# run: uv run --with shinywidgets[embedding_atlas] --with scikit-learn shiny run gallery/showcase_digits_atlas.py
# data: sklearn.datasets.load_digits() (bundled, no download)
import base64
import io

import numpy as np
import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from PIL import Image
from shiny.express import render, ui
from shinywidgets import render_embedding_atlas
from sklearn.datasets import load_digits
from sklearn.decomposition import PCA

digits = load_digits()
xy = PCA(n_components=2).fit_transform(digits.data)


def to_png_bytes(pixels: "np.ndarray", size: int = 64) -> bytes:
    img = Image.fromarray((pixels / 16 * 255).astype("uint8")).resize((size, size))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


docs = pd.DataFrame(
    {
        "digit": digits.target.astype(str),
        "image": [to_png_bytes(p) for p in digits.images],
        "x": xy[:, 0],
        "y": xy[:, 1],
    }
)

ui.page_opts(title=f"{len(docs):,} handwritten digits", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Embedding (colored by digit)")

        @render_embedding_atlas
        def atlas():
            return EmbeddingAtlasWidget(docs, x="x", y="y", image="image")

    with ui.card():
        ui.card_header("Selection")

        @render.text
        def count():
            sel = atlas.selected()
            return f"{len(sel):,} of {len(docs):,} digits selected"

        @render.ui
        def average_digit():
            sel = atlas.selected()
            # __row_index__ is the position in `docs` selected() was built
            # from, not the result's own (fresh) row index
            idx = sel["__row_index__"].to_numpy()
            mean_pixels = digits.images[idx].mean(axis=0)
            png = to_png_bytes(mean_pixels, size=160)
            b64 = base64.b64encode(png).decode()
            return ui.img(src=f"data:image/png;base64,{b64}", style="image-rendering: pixelated;")

        @render.ui
        def digit_breakdown():
            sel = atlas.selected()
            counts = sel["digit"].value_counts().sort_index()
            return ui.p(
                " · ".join(f"{d}: {n}" for d, n in counts.items()),
                class_="text-secondary small",
            )
