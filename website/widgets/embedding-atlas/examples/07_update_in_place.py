# The explorer ignores trait changes made from Python (setting
# `atlas.widget._predicate` or `._props` has no visible effect; there's no
# `change:_props` listener wired up for it on the frontend), so the only way
# to change what it shows is a re-render. A plain re-render would reset the
# user's pan/zoom/filter/coloring, though -- `_state` round-trips that view as
# JSON, so capturing it and passing it back as `initial_state` carries it
# across the data change below.
import json
from pathlib import Path

import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_embedding_atlas

ISSUES = pd.read_parquet(Path(__file__).parent / "data" / "issues.parquet")
COLUMNS = ["repo", "language", "state", "title", "text", "projection_x", "projection_y"]  # fmt: skip
REPOS = ["All repos", *sorted(ISSUES["repo"].unique())]

ui.page_opts(title="Re-render while carrying the view forward", fillable=True)
ui.input_select("repo", "Repo", REPOS)

last_state = reactive.value(None)


@reactive.effect
def _capture_state():
    s = atlas.read("_state")
    if s is not None:
        last_state.set(s)


@reactive.calc
def filtered():
    repo = input.repo()
    return ISSUES if repo == "All repos" else ISSUES[ISSUES["repo"] == repo]


with ui.card(full_screen=True):

    @render_embedding_atlas
    def atlas():
        df = filtered()
        with reactive.isolate():
            # NOT atlas.widget here: reading a renderer's own accessor/widget
            # inside its own render function cancels the render (see the
            # Gotchas section)
            prev = last_state.get()
        opts = {"initial_state": json.loads(prev)} if prev else {}
        return EmbeddingAtlasWidget(
            df[COLUMNS], x="projection_x", y="projection_y", text="text", **opts
        )

    @render.text
    def note():
        return f"{len(filtered()):,} rows loaded"
