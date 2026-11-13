# Fill behavior: with no explicit height, the output grows to fill its card
# (left, `full_screen=True` card). An explicit height (right) always wins --
# the explorer fits itself to it, growing or shrinking from its own 650px
# default. Outside a fillable container, give it at least 600px.
from pathlib import Path

import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import ui
from shinywidgets import render_embedding_atlas

ISSUES = pd.read_parquet(Path(__file__).parent / "data" / "issues.parquet")
COLUMNS = ["repo", "language", "state", "title", "text", "projection_x", "projection_y"]  # fmt: skip


def small_atlas():
    return EmbeddingAtlasWidget(
        ISSUES[COLUMNS], x="projection_x", y="projection_y", text="text"
    )


ui.page_opts(title="Fillable card vs. a fixed-height output", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Fills the card (no explicit height)")

        @render_embedding_atlas
        def atlas_fill():
            return small_atlas()

    with ui.card():
        ui.card_header('height="650px"')

        @render_embedding_atlas(height="650px")
        def atlas_fixed():
            return small_atlas()
