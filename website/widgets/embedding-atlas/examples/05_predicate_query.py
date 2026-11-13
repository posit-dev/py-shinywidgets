# predicate() is the cross-filter as a DuckDB WHERE expression, so you can
# push it into a query of your own instead of pulling the rows into Python
# first. Here it drives a server-side aggregate (average reactions) over a
# duckdb connection that's separate from the widget's own.
from pathlib import Path

import duckdb
import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import render, ui
from shinywidgets import render_embedding_atlas

ISSUES = pd.read_parquet(Path(__file__).parent / "data" / "issues.parquet")
COLUMNS = ["repo", "language", "state", "title", "text", "comments", "reactions", "projection_x", "projection_y"]  # fmt: skip

# `.register()` returns the connection; keep that as an assignment, not a
# bare statement -- shiny.express would otherwise treat its non-None result
# as a UI child, like it would a bare module-level docstring
con = duckdb.connect().register("issues", ISSUES)

ui.page_opts(title="predicate() driving a server-side aggregate", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_embedding_atlas
        def atlas():
            return EmbeddingAtlasWidget(
                ISSUES[COLUMNS], x="projection_x", y="projection_y", text="text"
            )

    with ui.card():
        ui.card_header("Average engagement, selected rows")

        @render.text
        def stat():
            where = atlas.predicate()
            clause = f"WHERE {where}" if where else ""
            n, reactions, comments = con.sql(
                f"SELECT count(*), avg(reactions), avg(comments) FROM issues {clause}"
            ).fetchone()
            return f"{n:,} issues · {reactions:.2f} avg reactions · {comments:.2f} avg comments"
