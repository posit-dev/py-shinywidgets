# selected() returns the rows passing the current cross-filter, as the same
# frame type (here pandas) the widget was built from -- a detail table for
# exactly what the user selected, with no SQL of your own to write.
from pathlib import Path

import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import render, ui
from shinywidgets import render_embedding_atlas

ISSUES = pd.read_parquet(Path(__file__).parent / "data" / "issues.parquet")
COLUMNS = ["repo", "language", "state", "title", "text", "projection_x", "projection_y"]  # fmt: skip

ui.page_opts(title="selected() as a detail table", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_embedding_atlas
        def atlas():
            return EmbeddingAtlasWidget(
                ISSUES[COLUMNS], x="projection_x", y="projection_y", text="text"
            )

    with ui.card(full_screen=True):
        ui.card_header("Selected rows")

        @render.data_frame
        def table():
            sel = atlas.selected()
            return sel[["repo", "state", "title"]].reset_index(drop=True)
