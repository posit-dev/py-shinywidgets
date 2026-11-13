import os

import numpy as np
import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import ui
from shinywidgets import render_embedding_atlas

N = int(os.environ.get("PERF_N", "10000"))
rng = np.random.default_rng(42)
df = pd.DataFrame(
    {
        "x": rng.normal(size=N),
        "y": rng.normal(size=N),
        "text": [f"doc {i}" for i in range(N)],
    }
)

ui.page_opts(title=f"embedding-atlas: {N:,} points", fillable=True)


@render_embedding_atlas
def atlas():
    # labels="disabled": isolates the payload/render-time cost of the GPU
    # map and the data load itself from auto-label clustering, which this
    # section isn't measuring.
    return EmbeddingAtlasWidget(df, x="x", y="y", text="text", labels="disabled")
