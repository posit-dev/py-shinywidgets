# A minimal Embedding Atlas explorer over a real dataset: 6,088 GitHub issues
# from the Shiny ecosystem (R and Python Shiny, bslib, shinywidgets, ...), with
# a 2D projection already computed offline (see "Computing a projection").
# Data: docs/showcase/issues/embed.py built data/issues.parquet from public
# GitHub issues using embedding_atlas.projection.compute_projection().
from pathlib import Path

import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import ui
from shinywidgets import render_embedding_atlas

ISSUES = pd.read_parquet(Path(__file__).parent / "data" / "issues.parquet")
COLUMNS = ["repo", "language", "state", "title", "text", "projection_x", "projection_y"]

ui.page_opts(title="Shiny issue atlas", fillable=True)

with ui.card(full_screen=True):

    @render_embedding_atlas
    def atlas():
        return EmbeddingAtlasWidget(
            ISSUES[COLUMNS], x="projection_x", y="projection_y", text="text"
        )
