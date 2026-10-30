from __future__ import annotations

import numpy as np
import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny import App, render, ui
from shinywidgets import output_widget, render_embedding_atlas

rng = np.random.default_rng(0)
N = 300
docs = pd.DataFrame(
    {
        "x": rng.normal(size=N),
        "y": rng.normal(size=N),
        "text": [f"item {i}" for i in range(N)],
        "group": rng.choice(["a", "b", "c"], size=N),
    }
)

app_ui = ui.page_fillable(
    ui.card(
        ui.card_header("Embedding Atlas"),
        output_widget("atlas"),
    ),
    ui.output_text("pred"),
    ui.output_text("nsel"),
)


def server(input, output, session):
    @render_embedding_atlas
    def atlas():
        return EmbeddingAtlasWidget(docs, x="x", y="y", text="text")

    @render.text
    def pred():
        return str(atlas.predicate())

    @render.text
    def nsel():
        return str(len(atlas.selection()))


app = App(app_ui, server)
