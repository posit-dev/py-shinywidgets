# Put PNG bytes in a column and pass it as `image=`: the explorer shows the
# image in hover tooltips and the detail table, alongside the auto-generated
# charts for every other column. Needs scikit-learn for the bundled digits
# dataset: `uv run --with scikit-learn shiny run 04_images.py`
import io

import numpy as np
import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from PIL import Image
from shiny.express import ui
from shinywidgets import render_embedding_atlas
from sklearn.datasets import load_digits
from sklearn.decomposition import PCA

digits = load_digits()
rng = np.random.default_rng(0)
idx = rng.choice(len(digits.images), size=600, replace=False)


def to_png(pixels: "np.ndarray") -> bytes:
    img = Image.fromarray((pixels / 16 * 255).astype("uint8")).resize((64, 64))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


xy = PCA(n_components=2).fit_transform(digits.data[idx])
docs = pd.DataFrame(
    {
        "digit": digits.target[idx].astype(str),
        "image": [to_png(p) for p in digits.images[idx]],
        "x": xy[:, 0],
        "y": xy[:, 1],
    }
)

ui.page_opts(title="Handwritten digits with image previews", fillable=True)

with ui.card(full_screen=True):

    @render_embedding_atlas
    def atlas():
        return EmbeddingAtlasWidget(docs, x="x", y="y", image="image")
