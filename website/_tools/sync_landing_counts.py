"""Rewrite the landing page's category-card counts from the Widgets sidebar in _quarto.yml.

The cards in index.qmd mirror the sidebar's widget groups, so the sidebar is the
source of truth for the counts. Run by `make docs` before rendering.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import yaml

WEBSITE = Path(__file__).resolve().parent.parent

CARD = re.compile(r'(<span class="n">)\d+(</span><div><h3>)([^<]+)(</h3>)')


def sidebar_widget_counts() -> dict[str, int]:
    config = yaml.safe_load((WEBSITE / "_quarto.yml").read_text())
    sidebars = config["website"]["sidebar"]
    guide = next(s for s in sidebars if s.get("id") == "guide")
    widgets = next(
        item for item in guide["contents"] if item.get("section") == "Widgets"
    )
    return {group["section"]: len(group["contents"]) for group in widgets["contents"]}


def main() -> int:
    counts = sidebar_widget_counts()
    qmd = WEBSITE / "index.qmd"
    text = qmd.read_text()

    card_titles = [html.unescape(m.group(3)) for m in CARD.finditer(text)]
    missing_cards = counts.keys() - set(card_titles)
    missing_sections = set(card_titles) - counts.keys()
    problems = [
        *(f"no landing card for sidebar group {name!r}" for name in missing_cards),
        *(
            f"landing card {name!r} has no sidebar group in _quarto.yml"
            for name in missing_sections
        ),
    ]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    def replace(m: re.Match[str]) -> str:
        count = f"{counts[html.unescape(m.group(3))]:02d}"
        return m.group(1) + count + m.group(2) + m.group(3) + m.group(4)

    updated = CARD.sub(replace, text)
    if updated == text:
        print("landing card counts already in sync")
    else:
        qmd.write_text(updated)
        print("updated landing card counts in index.qmd")
    return 0


if __name__ == "__main__":
    sys.exit(main())
