# Turn embedding vectors into the x/y columns an atlas needs, with
# embedding_atlas.projection.compute_projection(). A real app embeds raw text
# or images (modality="text"/"image", needs sentence-transformers); here the
# vectors are already computed, so modality="vector" skips straight to UMAP.
#
# compute_projection() can't run inside a Shiny app's own event loop (it
# calls asyncio.run() internally, which raises once a loop is already
# running -- the same reason Jupyter can't call it directly either). Compute
# it once, offline, the way docs/showcase/issues/embed.py does for the real
# GitHub-issues dataset used elsewhere in this guide:
#   uv run --with umap-learn python 02_compute_projection.py
# (UMAP's first call compiles its numba kernels, about a minute; reruns are
# fast.) Then view the cached result with `shiny run 02_compute_projection.py`.
from pathlib import Path

import numpy as np
import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import ui
from shinywidgets import render_embedding_atlas

CACHE = Path(__file__).parent / "data" / "projected_topics.parquet"


def build_cache() -> None:
    rng = np.random.default_rng(0)
    topics = {"astronomy": 0, "cooking": 1, "sailing": 2, "chess": 3}
    docs = pd.DataFrame(
        {
            "topic": [t for t in topics for _ in range(60)],
            "text": [f"{t} note {i}" for t in topics for i in range(60)],
        }
    )
    # 16-dim stand-ins for real text embeddings: one Gaussian cluster per topic
    centers = rng.normal(scale=4, size=(len(topics), 16))
    docs["vector"] = [
        (centers[topics[t]] + rng.normal(size=16)).tolist() for t in docs["topic"]
    ]

    # Imported here, not at module level: needs umap-learn, which only the
    # cache-building path below requires -- `shiny run` never hits this branch
    from embedding_atlas.projection import compute_projection

    docs = compute_projection(docs, inputs="vector", modality="vector", neighbors=None)
    docs.drop(columns=["vector"]).to_parquet(CACHE, index=False)


if __name__ == "__main__":
    build_cache()
    print(f"wrote {CACHE}")
else:
    docs = pd.read_parquet(CACHE)

    ui.page_opts(title="Projected from embedding vectors", fillable=True)

    with ui.card(full_screen=True):

        @render_embedding_atlas
        def atlas():
            return EmbeddingAtlasWidget(docs, x="projection_x", y="projection_y", text="text")
