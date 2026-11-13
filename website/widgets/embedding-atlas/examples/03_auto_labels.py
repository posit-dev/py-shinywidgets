# Automatic cluster labels are the library's default whenever `text` is
# given -- you don't pass anything to get them (the quick start already has
# them; this is the same data, cropped in on the embedding view itself). The
# `labels=` option is for supplying your own list of label dicts instead, not
# a flag to toggle the automatic ones (see Gotchas: the documented
# "automatic"/"disabled" sentinel strings don't work as described).
from pathlib import Path

import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import ui
from shinywidgets import render_embedding_atlas

ISSUES = pd.read_parquet(Path(__file__).parent / "data" / "issues.parquet")
COLUMNS = ["repo", "language", "title", "text", "projection_x", "projection_y"]

ui.page_opts(title="Auto-labeled issue clusters", fillable=True)

with ui.card(full_screen=True):

    @render_embedding_atlas
    def atlas():
        return EmbeddingAtlasWidget(
            ISSUES[COLUMNS], x="projection_x", y="projection_y", text="text"
        )
