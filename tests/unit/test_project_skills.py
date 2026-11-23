"""Guards for the repo-local project skills at .agents/skills/.

These skills are contributor-facing (they teach agents the repo's own
workflows) and are not shipped. The drift risk is repo references going
stale as the codebase evolves, so these tests check the frontmatter
contract and that every repo-root-relative path a skill mentions exists.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"

# Backticked repo-root-relative paths: `tests/unit/`, `shinywidgets/_comm.py`.
# Tokens with placeholders (`website/widgets/<slug>/`) don't match and are
# skipped.
PATH_RE = re.compile(r"`((?:[\w.-]+/)+[\w.-]*(?:\.(?:py|md|toml|ya?ml|txt|cfg))?)`")


def skill_dirs() -> list[Path]:
    if not SKILLS_ROOT.exists():
        return []
    return sorted(d for d in SKILLS_ROOT.iterdir() if (d / "SKILL.md").is_file())


@pytest.mark.parametrize("skill", skill_dirs(), ids=lambda d: d.name)
def test_frontmatter_contract(skill: Path) -> None:
    text = (skill / "SKILL.md").read_text()
    match = re.match(r"^---\n(.*?\n)---\n", text, re.DOTALL)
    assert match, f"{skill} has no YAML frontmatter block"
    meta: dict[str, Any] = yaml.safe_load(match.group(1))
    assert meta["name"] == skill.name
    assert 0 < len(meta["description"]) <= 1024


@pytest.mark.parametrize("skill", skill_dirs(), ids=lambda d: d.name)
def test_repo_paths_resolve(skill: Path) -> None:
    text = (skill / "SKILL.md").read_text()
    broken = [p for p in set(PATH_RE.findall(text)) if not (REPO_ROOT / p).exists()]
    assert broken == []
