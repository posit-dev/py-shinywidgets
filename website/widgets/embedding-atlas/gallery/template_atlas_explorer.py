# title: Atlas + live stats + detail table
# bucket: template
# description: A reusable starting point: an embedding atlas next to a stat
#   line (from predicate()) and a detail table (from selected()). Swap DATA,
#   COLUMNS and the x/y/text columns for your own data.
# run: uv run --with shinywidgets[embedding_atlas] shiny run gallery/template_atlas_explorer.py
# data: docs/showcase/issues/data/issues.parquet (6,088 real GitHub issues
#   from the Shiny ecosystem, with a projection precomputed offline)
from pathlib import Path

import duckdb
import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import render, ui
from shinywidgets import render_embedding_atlas

DATA = Path(__file__).parent.parent / "examples" / "data" / "issues.parquet"
COLUMNS = ["repo", "language", "state", "title", "text", "comments", "projection_x", "projection_y"]  # fmt: skip
X, Y, TEXT = "projection_x", "projection_y", "text"

df = pd.read_parquet(DATA)[COLUMNS]
# Chained as an assignment, not a bare statement: shiny.express would
# otherwise capture .register()'s non-None return as a UI child
con = duckdb.connect().register("rows", df)

ui.page_opts(title="Atlas explorer template", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_embedding_atlas
        def atlas():
            return EmbeddingAtlasWidget(df, x=X, y=Y, text=TEXT)

    with ui.card(full_screen=True):
        ui.card_header("Selection")

        @render.text
        def stat():
            where = atlas.predicate()
            clause = f"WHERE {where}" if where else ""
            (n,) = con.sql(f"SELECT count(*) FROM rows {clause}").fetchone()
            return f"{n:,} of {len(df):,} rows"

        @render.data_frame
        def table():
            sel = atlas.selected().drop(columns=[X, Y, "__row_index__"])
            return sel.reset_index(drop=True)
