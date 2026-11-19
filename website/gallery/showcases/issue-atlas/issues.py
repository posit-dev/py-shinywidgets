import re
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import pandas as pd

REPOS: tuple[str, ...] = (
    "rstudio/shiny",
    "posit-dev/py-shiny",
    "rstudio/bslib",
    "rstudio/htmltools",
    "posit-dev/py-shinywidgets",
    "rstudio/shinytest2",
    "posit-dev/shinychat",
    "rstudio/shinydashboard",
    "rstudio/shiny-server",
)
R_REPOS: frozenset[str] = frozenset({"shiny", "bslib", "htmltools", "shinydashboard", "shinytest2"})
MAX_SUMMARY_TITLES = 150

CODE_FENCE = re.compile(r"(```|~~~).*?(\1|$)", re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?(-->|$)", re.DOTALL)
URL = re.compile(r"https?://\S+")
WHITESPACE = re.compile(r"\s+")


def language_of(repo: str) -> Literal["R", "Python", "Chat"]:
    if repo.startswith("posit-dev/py"):
        return "Python"
    if repo.endswith("shinychat"):
        return "Chat"
    return "R"


def clean_body(body: str | None, max_chars: int = 1000) -> str:
    if not body:
        return ""
    text = CODE_FENCE.sub(" ", body)
    text = HTML_COMMENT.sub(" ", text)
    text = URL.sub(" ", text)
    return WHITESPACE.sub(" ", text).strip()[:max_chars]


def find_twins(df: pd.DataFrame, max_dist: float = 0.2) -> pd.Series:
    repos = df["repo"].tolist()
    created = df["created_at"].tolist()
    twins: list[int | None] = []
    for i, (lang, neighbors) in enumerate(zip(df["language"], df["neighbors"])):
        twin = None
        if lang == "Python":
            pairs = list(zip(neighbors["ids"], neighbors["distances"]))[1:]
            for j, dist in pairs:
                j = int(j)
                if dist <= max_dist and repos[j] in R_REPOS and created[j] < created[i]:
                    twin = j
                    break
        twins.append(twin)
    return pd.Series(twins, index=df.index, dtype="Int64")


def prep_repo(
    repo: str,
    raw_dir: Path,
    fetch: Callable[[str], str],
    refresh: bool = False,
) -> int:
    out = raw_dir / f"{repo.replace('/', '_')}.jsonl"
    if refresh or not out.exists():
        tmp = out.with_suffix(".tmp")
        tmp.write_text(fetch(repo))
        tmp.replace(out)
    with open(out) as f:
        return sum(1 for line in f if line.strip())


def summary_titles(sel: pd.DataFrame, n: int = MAX_SUMMARY_TITLES) -> list[str]:
    return sel.sort_values("comments", ascending=False, kind="stable")["title"].head(n).tolist()
