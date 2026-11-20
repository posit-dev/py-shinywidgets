# Title: The Shiny issue atlas
# Bucket: showcase (~206 lines)
# Description: 6,088 GitHub issues from 9 Shiny-ecosystem repos, embedded
#   with sentence-transformers and projected with embedding-atlas. Select a
#   region to see Python issues sitting next to an older R twin asking the
#   same thing, or ask Claude to summarize the selection.
# Run: shiny run app.py
#   (the "Summarize selection" button needs ANTHROPIC_API_KEY; everything
#   else works without it. The map needs a WebGPU-capable browser.)
# Data: GitHub Issues API + all-MiniLM-L6-v2 embeddings (3 MB parquet,
#   downloaded on first run; rebuild with prep_data.py then embed.py).

import os
import shutil
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_embedding_atlas

from issues import summary_titles
from summarize import make_chat, summarize

DATA_URL = "https://github.com/cpsievert/py-shinywidgets-data/releases/download/showcase-v1/issues.parquet"
DATA = Path(__file__).parent / "data" / "issues.parquet"

if not DATA.exists():
    DATA.parent.mkdir(exist_ok=True)
    print(f"Downloading {DATA.name} (~3 MB, one time) ...", flush=True)
    tmp = DATA.with_suffix(".part")
    with urllib.request.urlopen(DATA_URL) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f, length=1 << 20)
    tmp.rename(DATA)
ISSUES = pd.read_parquet(DATA)
ATLAS_COLUMNS = [
    "repo", "language", "state", "year", "title", "text", "labels", "comments", "reactions",
    "projection_x", "projection_y", "neighbors",
]  # fmt: skip
STOP_WORDS = [
    "hi", "hello", "question", "want", "wanted", "user", "users", "using", "use", "used", "would", "like",
    "issue", "issues", "error", "errors", "shiny", "app", "apps", "get", "getting", "example", "work",
    "works", "working", "able", "need", "needs", "way", "add", "adding", "support", "please", "thanks",
    "thank", "trying", "try", "also", "one", "set", "function", "new", "make", "possible", "bug",
    "feature", "request", "package", "seems", "think", "know", "could", "should", "currently", "doesn",
    "don", "isn", "can", "cannot", "case", "instead", "see", "run", "running", "time", "problem",
    "expected", "behavior", "behaviour", "reprex", "session", "info", "version", "describe",
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "it", "this", "that", "be",
    "are", "was", "as", "at", "by", "from", "not", "no", "if", "when", "you", "your", "we", "i", "my", "me",
    "there", "which", "but", "so", "do", "does", "have", "has", "how", "what", "any", "all", "some", "more",
    "into", "only", "other", "than", "then", "them", "they", "their", "these", "those", "will", "out", "up",
]  # fmt: skip
N_TWINS = int(ISSUES["twin"].notna().sum())

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.output_ui("stats"),
        ui.hr(class_="my-2"),
        ui.h6("Asked twice: Python issues with an older R twin"),
        ui.output_ui("asked_twice"),
        ui.hr(class_="my-2"),
        ui.output_ui("summarize_button"),
        ui.output_ui("summary"),
        ui.p(
            "Drag on the map to select a region (shift + drag, or toggle the "
            "rectangle/lasso tool below the map).",
            class_="text-secondary small mt-auto mb-0",
        ),
        width=420,
        gap="0.5rem",
    ),
    ui.input_dark_mode(mode="dark", style="display: none"),
    ui.tags.script(
        """new MutationObserver(() => {
          const dark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
          document.body.classList.toggle('dark', dark); document.body.classList.toggle('light', !dark);
        }).observe(document.documentElement, {attributes: true, attributeFilter: ['data-bs-theme']});"""
    ),
    ui.tags.style(
        """
        .sidebar-content { display: flex; flex-direction: column; height: 100%; }
        .twin { font-size: .85rem; line-height: 1.25; padding: .35rem 0; border-bottom: 1px solid var(--bs-border-color); }
        .twin a { text-decoration: none; }
        .twin .meta { color: var(--bs-secondary-color); }
        #asked_twice { display: block; max-height: 34vh; overflow-y: auto; }
        #summary { font-size: .9rem; }
        """
    ),
    ui.card(output_widget("atlas"), class_="p-0"),
    title=f"The Shiny issue atlas: {len(ISSUES):,} issues from 9 repos",
    fillable=True,
)


def server(input: Any, output: Any, session: Any) -> None:
    @render_embedding_atlas
    def atlas():
        return EmbeddingAtlasWidget(
            ISSUES[ATLAS_COLUMNS],
            x="projection_x",
            y="projection_y",
            text="text",
            neighbors="neighbors",
            stop_words=STOP_WORDS,
        )

    @reactive.calc
    def selected() -> pd.DataFrame | None:
        w = atlas.widget
        if w is None or reactive_read(w, "_predicate") is None:
            return None
        rows = w.selection()["__row_index__"].to_numpy()
        return ISSUES.iloc[rows]

    has_selection = reactive.value(False)

    @reactive.effect
    def _track_selection():
        sel = selected()
        has_selection.set(sel is not None and 0 < len(sel) < len(ISSUES))

    @render.ui
    def stats():
        sel = selected()
        df = ISSUES if sel is None else sel
        label = "All issues" if sel is None else "Selected"
        if not len(df):
            return ui.p("Nothing selected.", id="stats-n", data_n="0")
        by_lang = df["language"].value_counts()
        langs = " · ".join(f"{lang} {by_lang.get(lang, 0):,}" for lang in ["R", "Python", "Chat"])
        return ui.div(
            ui.h4(f"{len(df):,}", class_="mb-0", id="stats-n", data_n=str(len(df))),
            ui.p(f"{label} · {(df['state'] == 'open').mean():.0%} open", class_="mb-0"),
            ui.p(langs, class_="text-secondary small mb-0"),
        )

    @render.ui
    def asked_twice():
        sel = selected()
        df = ISSUES if sel is None else sel
        pairs = df[df["twin"].notna()]
        if sel is None:
            return ui.p(
                f"{N_TWINS} Python issues sit right next to an older R issue asking the same thing. "
                "Select a region of the map to see them.",
                class_="text-secondary small mb-0",
            )
        if pairs.empty:
            return ui.p("No Python issue here has an older R twin.", class_="text-secondary small mb-0")
        twins = ISSUES.iloc[pairs["twin"].astype(int).to_numpy()].reset_index(drop=True)
        rows = pd.concat([pairs.reset_index(drop=True), twins.add_prefix("r_")], axis=1)
        rows = rows.sort_values("r_created_at")
        return ui.div(*[twin_item(r) for r in rows.itertuples()])

    @ui.bind_task_button(button_id="summarize")
    @reactive.extended_task
    async def summarize_task(key: int, titles: list[str]) -> tuple[int, str]:
        return key, await summarize(titles, make_chat())

    @render.ui
    def summarize_button():
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return ui.p("Set ANTHROPIC_API_KEY to ask Claude what a selection of issues shares.",
                        class_="text-secondary small mb-0")  # fmt: skip
        if not has_selection():
            return ui.p("Select a region to ask Claude what those issues share.", class_="text-secondary small mb-0")
        return ui.input_task_button("summarize", "Summarize selection", label_busy="Reading issues...")

    @reactive.effect
    @reactive.event(input.summarize)
    def _start_summary():
        sel = selected()
        if sel is not None and len(sel):
            summarize_task.invoke(selection_key(sel), summary_titles(sel))

    @render.ui
    def summary():
        sel = selected()
        if sel is None or summarize_task.status() != "success":
            return None
        key, text = summarize_task.result()
        if key != selection_key(sel):
            return None
        return ui.div(ui.p(text, class_="mb-0"), class_="mt-2", id="summary-text")


def twin_item(r: Any) -> ui.Tag:
    return ui.div(
        ui.a(f"{r.repo} #{r.number}", href=r.url, target="_blank"),
        ui.span(f" ({r.year}, {r.state}) ", class_="meta"),
        ui.span(r.title),
        ui.br(),
        "↳ ",
        ui.a(f"{r.r_repo} #{r.r_number}", href=r.r_url, target="_blank"),
        ui.span(f" ({r.r_year}, {r.r_state}) ", class_="meta"),
        ui.span(r.r_title),
        class_="twin",
    )


def selection_key(sel: pd.DataFrame) -> int:
    return hash(tuple(sel.index))


app = App(app_ui, server)
