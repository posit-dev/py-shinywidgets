# Pattern: atlas crossfilter -> a plotly chart of exactly the selected rows.
# predicate() is a DuckDB WHERE expression over the *same* column names the
# widget was built from, so it applies directly to a pandas boolean mask via
# a second DuckDB connection registered on the same frame -- no need to
# touch the widget's own (locked-down) connection. Pairs with the plotly guide.
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import render, ui
from shinywidgets import render_embedding_atlas, render_plotly

ISSUES = pd.read_parquet(Path(__file__).parent / "data" / "issues.parquet")
COLUMNS = ["repo", "language", "state", "title", "text", "projection_x", "projection_y"]  # fmt: skip

# Chained as an assignment, not a bare statement: shiny.express would
# otherwise capture .register()'s non-None return as a UI child
con = duckdb.connect().register("issues", ISSUES)

ui.page_opts(title="Crossfilter driving a plotly breakdown", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_embedding_atlas
        def atlas():
            return EmbeddingAtlasWidget(
                ISSUES[COLUMNS], x="projection_x", y="projection_y", text="text"
            )

    with ui.card():
        ui.card_header("Language mix of the current selection")

        @render_plotly
        def breakdown():
            where = atlas.predicate()
            clause = f"WHERE {where}" if where else ""
            counts = con.sql(
                f"SELECT language, count(*) AS n FROM issues {clause} GROUP BY language"
            ).df()
            return px.bar(counts, x="language", y="n", text="n")
