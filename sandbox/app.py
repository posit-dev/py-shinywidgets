from __future__ import annotations
import numpy as np, pandas as pd
from shiny import App, ui
from shinywidgets import output_widget, render_widget, reactive_read
from embedding_atlas.widget import EmbeddingAtlasWidget

app_ui = ui.page_fillable(
    ui.card(ui.card_header("atlas"), output_widget("atlas"), full_screen=True),
)

def server(input, output, session):
    @render_widget
    def atlas():
        rng = np.random.default_rng(0)
        n = 500
        df = pd.DataFrame({"x": rng.normal(size=n), "y": rng.normal(size=n), "text": [f"item {i}" for i in range(n)], "g": rng.choice(list("abc"), n)})
        return EmbeddingAtlasWidget(df, x="x", y="y", text="text")
app = App(app_ui, server)
