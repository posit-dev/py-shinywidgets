# Read on demand: export the explorer's current selection as a CSV, read
# only when the user clicks Download -- no warm-up needed, since
# selected() is live from the moment the explorer renders.
from pathlib import Path

import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny import render
from shiny.express import ui
from shinywidgets import render_embedding_atlas

ISSUES = pd.read_parquet(Path(__file__).parent / "data" / "issues.parquet")
COLUMNS = ["repo", "language", "state", "title", "text", "projection_x", "projection_y"]  # fmt: skip

ui.page_opts(title="Export the current selection, read on demand", fillable=True)

with ui.layout_columns(col_widths=[9, 3]):
    with ui.card(full_screen=True):

        @render_embedding_atlas
        def atlas():
            return EmbeddingAtlasWidget(
                ISSUES[COLUMNS], x="projection_x", y="projection_y", text="text"
            )

    with ui.card():
        ui.card_header("Export")
        "Download exactly the issues currently selected (chart click, box, or lasso)."

        @render.download_button(filename="issues_selected.csv", label="Download CSV")
        def download():
            sel = atlas.selected()
            yield sel[["repo", "state", "title"]].to_csv(index=False)
