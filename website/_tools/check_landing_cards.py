"""Check the landing page's category cards against the Widgets sidebar in _quarto.yml.

The cards in index.qmd mirror the sidebar's widget groups, so the sidebar is the
source of truth. Run by `make docs` before rendering.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import yaml

WEBSITE = Path(__file__).resolve().parent.parent

CARD = re.compile(r"<div><h3>([^<]+)</h3>")


def sidebar_widget_groups() -> set[str]:
    config = yaml.safe_load((WEBSITE / "_quarto.yml").read_text())
    sidebars = config["website"]["sidebar"]
    guide = next(s for s in sidebars if s.get("id") == "guide")
    widgets = next(
        item for item in guide["contents"] if item.get("section") == "Widgets"
    )
    return {group["section"] for group in widgets["contents"]}


def main() -> int:
    groups = sidebar_widget_groups()
    card_titles = {
        html.unescape(t) for t in CARD.findall((WEBSITE / "index.qmd").read_text())
    }
    problems = [
        *(
            f"no landing card for sidebar group {name!r}"
            for name in groups - card_titles
        ),
        *(
            f"landing card {name!r} has no sidebar group in _quarto.yml"
            for name in card_titles - groups
        ),
    ]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print("landing cards match the Widgets sidebar groups")
    return 0


if __name__ == "__main__":
    sys.exit(main())
