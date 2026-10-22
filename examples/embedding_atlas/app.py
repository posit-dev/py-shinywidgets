import duckdb
import numpy as np
import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_embedding_atlas

rng = np.random.default_rng(1)

# Four clusters of "documents". A real app would use a 2D projection of text
# embeddings (e.g., from embedding_atlas.projection.compute_text_projection());
# the explorer only needs the x/y columns.
topics = {
    "astronomy": ((-4, 3), ["star", "orbit", "galaxy", "comet", "nebula"]),
    "cooking": ((4, 3), ["sauce", "bake", "simmer", "whisk", "roast"]),
    "sailing": ((-4, -3), ["keel", "tack", "jib", "harbor", "gale"]),
    "chess": ((4, -3), ["pawn", "gambit", "castle", "fork", "endgame"]),
}
rows = []
for topic, ((cx, cy), words) in topics.items():
    for _ in range(300):
        rows.append(
            {
                "x": rng.normal(cx, 1.2),
                "y": rng.normal(cy, 1.2),
                "topic": topic,
                "text": " ".join(rng.choice(words, 4)),
            }
        )
docs = pd.DataFrame(rows)

app_ui = ui.page_fillable(
    ui.layout_columns(
        ui.card(
            ui.card_header("Explore the embedding"),
            output_widget("atlas"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Selection in Python"),
            ui.output_text("summary"),
            ui.output_data_frame("selected"),
        ),
        col_widths=[8, 4],
    ),
    title="Embedding Atlas",
)


def server(input, output, session):
    @render_embedding_atlas
    def atlas():
        # The explorer runs its queries by sending SQL from the browser to this
        # connection, so any visitor can run any SQL on it. Lock it down once the
        # widget has loaded its data, so that SQL can't read or write server files.
        # (Use a new connection per widget: two widgets can't share one.)
        con = duckdb.connect()
        widget = EmbeddingAtlasWidget(docs, x="x", y="y", text="text", connection=con)
        con.execute("SET enable_external_access = false")
        con.execute("SET lock_configuration = true")
        return widget

    # The widget syncs the filter the user builds in the browser (a SQL predicate)
    # back to Python, where selection() applies it to the data. `_predicate` is
    # upstream-internal, but it's the only selection state the widget syncs.
    @reactive.calc
    def selection() -> pd.DataFrame:
        reactive_read(atlas.widget, "_predicate")
        return atlas.widget.selection()

    @render.text
    def summary():
        return f"{len(selection())} of {len(docs)} points selected"

    @render.data_frame
    def selected():
        return selection().drop(columns=["x", "y", "__row_index__"]).head(100)


app = App(app_ui, server)
