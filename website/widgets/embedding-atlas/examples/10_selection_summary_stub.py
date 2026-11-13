# Pattern: selected() -> a one-line summary of what the user circled. This
# guide can't call a real LLM (no API keys), so `stub_summary()` below ranks
# keywords by frequency as a stand-in. The release showcase
# (docs/showcase/issues/summarize.py) wires the same selection into a real
# call: `await ChatAnthropic(model=..., system_prompt=...).chat_async(prompt)`
# with the selected titles in the prompt -- swap `stub_summary` for that.
import re
from collections import Counter
from pathlib import Path

import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny.express import render, ui
from shinywidgets import render_embedding_atlas

ISSUES = pd.read_parquet(Path(__file__).parent / "data" / "issues.parquet")
COLUMNS = ["repo", "language", "state", "title", "text", "projection_x", "projection_y"]  # fmt: skip
STOP_WORDS = {"the", "a", "an", "to", "in", "on", "for", "and", "is", "of", "with"}


def stub_summary(titles: list[str]) -> str:
    words = [w for t in titles for w in re.findall(r"[a-z]+", t.lower())]
    top = Counter(w for w in words if w not in STOP_WORDS).most_common(3)
    return f"{len(titles)} issues, mostly about: {', '.join(w for w, _ in top)}"


ui.page_opts(title="Selection summary (stand-in for an LLM call)", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_embedding_atlas
        def atlas():
            return EmbeddingAtlasWidget(
                ISSUES[COLUMNS], x="projection_x", y="projection_y", text="text"
            )

    with ui.card():
        ui.card_header("Summary of the selection")

        @render.text
        def summary():
            sel = atlas.selected()
            if len(sel) == len(ISSUES):
                return "Select a region to summarize it."
            return stub_summary(sel["title"].tolist())
