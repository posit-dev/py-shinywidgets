"""Guards for the bundled Agent Skill shipped at shinywidgets/.agents/skills/shinywidgets/.

See AGENTS.md's "Bundled Agent Skill" section for the maintenance rule this
file enforces: a PR that changes public API/behavior or a guide page's
guidance updates the matching skill file in the same PR.
"""

from __future__ import annotations

import ast
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import pytest
import shinywidgets
import yaml
from shinywidgets._render_widget import render_widget

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "shinywidgets" / ".agents" / "skills" / "shinywidgets"
REFERENCES = SKILL_DIR / "references"
QUARTO_YML = REPO_ROOT / "website" / "_quarto.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Pages whose widget gets no dedicated `render_*` (name minus "render_" is
# wrong or ambiguous); everything else uses the default.
RENDERER_SLUG_OVERRIDES = {
    "render_mosaic_widget": "mosaic",
    "render_embedding_atlas": "embedding-atlas",
}


def published_widget_slugs() -> list[str]:
    """Slugs under the website's Widgets sidebar section, in `_quarto.yml`."""
    if not QUARTO_YML.exists():
        return []
    data = yaml.safe_load(QUARTO_YML.read_text())
    sidebar = data["website"]["sidebar"][0]["contents"]
    widgets_section = next(s for s in sidebar if s.get("section") == "Widgets")
    slugs: list[str] = []
    for group in widgets_section["contents"]:
        for entry in group["contents"]:
            path = entry if isinstance(entry, str) else entry["href"]
            match = re.fullmatch(r"widgets/([^/]+)/index\.md", path)
            if match:
                slugs.append(match.group(1))
    return slugs


def public_renderers() -> list[str]:
    """`render_*` names in `shinywidgets.__all__`, minus the generic base."""
    return [
        name
        for name in shinywidgets.__all__
        if name.startswith("render_") and name != "render_widget"
    ]


def slug_for(renderer_name: str) -> str:
    return RENDERER_SLUG_OVERRIDES.get(renderer_name, renderer_name[len("render_") :])


def accessors(renderer: type) -> list[str]:
    """Public names on `renderer` that aren't inherited from `render_widget`."""
    base_names = set(dir(render_widget))
    return [
        name
        for name in dir(renderer)
        if not name.startswith("_") and name not in base_names
    ]


def all_reference_files() -> list[Path]:
    if not REFERENCES.exists():
        return []
    return sorted(REFERENCES.rglob("*.md"))


def all_skill_files() -> list[Path]:
    if not SKILL_DIR.exists():
        return []
    skill_md = [SKILL_DIR / "SKILL.md"] if (SKILL_DIR / "SKILL.md").exists() else []
    return skill_md + all_reference_files()


def test_frontmatter_contract() -> None:
    meta = frontmatter(SKILL_DIR / "SKILL.md")
    assert meta["name"] == SKILL_DIR.name == "shinywidgets"
    assert 0 < len(meta["description"]) <= 1024


def test_skill_md_word_budget() -> None:
    assert word_count(SKILL_DIR / "SKILL.md") <= 1600


@pytest.mark.parametrize("path", all_reference_files(), ids=str)
def test_reference_word_budget(path: Path) -> None:
    limit = 900 if path.parent.name == "widgets" else 1100
    assert word_count(path) <= limit


def test_links_resolve_and_every_reference_is_indexed() -> None:
    linked = set(re.findall(r"`(references/[^`]+\.md)`", read(SKILL_DIR / "SKILL.md")))
    on_disk = {p.relative_to(SKILL_DIR).as_posix() for p in REFERENCES.rglob("*.md")}
    assert linked == on_disk


@pytest.mark.parametrize("path", all_reference_files(), ids=str)
def test_reference_relative_links_resolve(path: Path) -> None:
    targets = re.findall(r"\]\(([^)\s#]+\.md)(?:#[^)]*)?\)", read(path))
    broken = [t for t in targets if not (path.parent / t).is_file()]
    assert broken == []


def test_widget_references_match_published_pages() -> None:
    if not QUARTO_YML.exists():
        pytest.skip(
            "website/_quarto.yml is not available (e.g., running from an sdist)"
        )
    assert {p.stem for p in (REFERENCES / "widgets").glob("*.md")} == set(
        published_widget_slugs()
    )


STAMP_RE = re.compile(r"^Written against `([\w.-]+)` (\d+)\.x\.$", re.MULTILINE)


@pytest.mark.parametrize(
    "path", sorted((REFERENCES / "widgets").glob("*.md")), ids=lambda p: p.stem
)
def test_widget_reference_has_version_stamp(path: Path) -> None:
    assert STAMP_RE.search(read(path)), (
        f"{path.name} has no version stamp; add a final line like "
        "'Written against `plotly` 6.x.'"
    )


@pytest.mark.parametrize(
    "path", sorted((REFERENCES / "widgets").glob("*.md")), ids=lambda p: p.stem
)
def test_version_stamp_matches_installed(path: Path) -> None:
    match = STAMP_RE.search(read(path))
    assert match, f"{path.name} has no version stamp"
    pkg, major = match.groups()
    try:
        installed = version(pkg)
    except PackageNotFoundError:
        pytest.skip(f"{pkg} is not installed in this environment")
    assert installed.split(".")[0] == major, (
        f'{path.name} is stamped "{pkg} {major}.x" but {pkg} {installed} is '
        "installed. A new major version means this reference needs re-auditing:\n"
        "1. Check the upstream changelog for changes affecting this page's claims\n"
        "2. Run the page's quick start and verify it still works\n"
        "3. Update any stale advice (and the website page, per the maintenance rule)\n"
        f'4. Bump the stamp to "Written against `{pkg}` {installed.split(".")[0]}.x."\n'
        'See AGENTS.md "When a widget library releases a new major version".'
    )


@pytest.mark.parametrize("name", public_renderers())
def test_renderer_is_indexed_and_documented(name: str) -> None:
    assert name in read(SKILL_DIR / "SKILL.md")
    ref = REFERENCES / "widgets" / f"{slug_for(name)}.md"
    text = read(ref)
    assert name in text
    renderer = getattr(shinywidgets, name)
    for acc in accessors(renderer):
        assert re.search(rf"[`.]{re.escape(acc)}\b", text), (
            f"{acc} missing from {ref.name}"
        )


def test_mentioned_extras_exist() -> None:
    extras = {normalize(e) for e in pyproject()["project"]["optional-dependencies"]}
    for path in [SKILL_DIR / "SKILL.md", *all_reference_files()]:
        for group in re.findall(r"shinywidgets\[([^\]]+)\]", read(path)):
            for e in group.split(","):
                assert normalize(e.strip()) in extras, (path.name, e)


@pytest.mark.parametrize("path", all_skill_files(), ids=str)
def test_python_blocks_parse_and_import_public_names(path: Path) -> None:
    for block in python_blocks(read(path)):
        tree = ast.parse(block)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "shinywidgets":
                for alias in node.names:
                    assert alias.name in shinywidgets.__all__


def frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text()
    match = re.match(r"^---\n(.*?\n)---\n", text, re.DOTALL)
    assert match, f"{path} has no YAML frontmatter block"
    return yaml.safe_load(match.group(1))


def word_count(path: Path) -> int:
    return len(read(path).split())


def read(path: Path) -> str:
    return path.read_text()


def python_blocks(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, re.DOTALL)


def normalize(name: str) -> str:
    """PEP 685 extra-name normalization: lowercase, `_` -> `-`."""
    return name.strip().lower().replace("_", "-")


def pyproject() -> dict[str, Any]:
    with PYPROJECT.open("rb") as f:
        return tomllib.load(f)
