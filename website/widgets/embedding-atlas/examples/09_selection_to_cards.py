# Pattern: lasso/filter -> a linked detail list, built from selected()
# instead of a plain data_frame so each row can carry a live link.
from pathlib import Path

import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import render, ui
from shinywidgets import render_embedding_atlas

ISSUES = pd.read_parquet(Path(__file__).parent / "data" / "issues.parquet")
COLUMNS = ["repo", "language", "state", "title", "text", "url", "projection_x", "projection_y"]  # fmt: skip

ui.page_opts(title="Selection as linked detail cards", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_embedding_atlas
        def atlas():
            return EmbeddingAtlasWidget(
                ISSUES[COLUMNS], x="projection_x", y="projection_y", text="text"
            )

    with ui.card(full_screen=True):
        ui.card_header("Selected issues")

        @render.ui
        def cards():
            sel = atlas.selected()
            if len(sel) == len(ISSUES):
                return ui.p("Select a region or click a bar to see issues here.")
            rows = sel.sort_values("state").head(15)
            return ui.div(
                *[
                    ui.p(
                        ui.a(f"{r.repo} ({r.state})", href=r.url, target="_blank"),
                        ": ",
                        r.title,
                        class_="mb-2",
                    )
                    for r in rows.itertuples()
                ]
            )
