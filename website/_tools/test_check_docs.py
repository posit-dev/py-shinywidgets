from pathlib import Path

from check_docs import (
    Fence,
    check_links,
    check_gallery_run,
    check_snippets,
    parse_fence,
    slugify,
)


def test_matching_snippet_passes(tmp_path: Path) -> None:
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "a.py").write_text("import a\nprint(a)\n")
    md = tmp_path / "guide.md"
    md.write_text('```{.python file="examples/a.py"}\nimport a\nprint(a)\n```\n')

    assert check_snippets(md) == []


def test_mismatched_snippet_reported(tmp_path: Path) -> None:
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "a.py").write_text("import a\nprint(a)\n")
    md = tmp_path / "guide.md"
    md.write_text(
        '```{.python file="examples/a.py"}\nimport a\nprint("different")\n```\n'
    )

    problems = check_snippets(md)

    assert len(problems) == 1
    assert "examples/a.py" in problems[0]


def test_untagged_snippet_reported(tmp_path: Path) -> None:
    md = tmp_path / "guide.md"
    md.write_text("Some prose.\n\n```python\nprint('hi')\n```\n")

    problems = check_snippets(md)

    assert len(problems) == 1
    assert "untagged snippet" in problems[0]


def test_skipped_snippet_passes(tmp_path: Path) -> None:
    md = tmp_path / "guide.md"
    md.write_text("<!-- snippet: skip -->\n```python\nprint('hi')\n```\n")

    assert check_snippets(md) == []


def test_missing_extra_file_reported(tmp_path: Path) -> None:
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "a.py").write_text("import a\n")
    md = tmp_path / "guide.md"
    md.write_text('```{.python file="examples/a.py" files="nope.py"}\nimport a\n```\n')

    problems = check_snippets(md)

    assert len(problems) == 1
    assert "nope.py" in problems[0]


def test_bad_collapse_reported(tmp_path: Path) -> None:
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "a.py").write_text("import a\n")
    md = tmp_path / "guide.md"
    md.write_text('```{.python file="examples/a.py" collapse="yes"}\nimport a\n```\n')

    problems = check_snippets(md)

    assert len(problems) == 1
    assert "collapse" in problems[0]


def test_parse_fence() -> None:
    assert parse_fence('  ```{.python file="examples/a.py" collapse="true"}') == Fence(
        "  ", "python", {"file": "examples/a.py", "collapse": "true"}
    )
    assert parse_fence("```") is None
    assert parse_fence("```python") == Fence("", "python", {})


def test_missing_link_target_reported(tmp_path: Path) -> None:
    md = tmp_path / "guide.md"
    md.write_text("See [x](missing.md) for more.\n")

    problems = check_links(md)

    assert len(problems) == 1
    assert "missing.md" in problems[0]


def test_anchor_slug(tmp_path: Path) -> None:
    other = tmp_path / "other.md"
    other.write_text("## 1. Selection &rarr; table of rows\n\nBody text.\n")

    ok_md = tmp_path / "ok.md"
    ok_md.write_text("See [x](other.md#1-selection--table-of-rows).\n")
    assert check_links(ok_md) == []

    bad_md = tmp_path / "bad.md"
    bad_md.write_text("See [x](other.md#nope).\n")
    problems = check_links(bad_md)
    assert len(problems) == 1


CLONE = "git clone --depth 1 https://github.com/posit-dev/py-shinywidgets"


def gallery_page(tmp_path: Path, kind: str, slug: str, body: str) -> Path:
    dir = tmp_path / "gallery" / kind / slug
    dir.mkdir(parents=True)
    md = dir / "index.md"
    md.write_text(body)
    return md


def run_block(kind: str, slug: str, command: str) -> str:
    return f"```sh\n{CLONE}\ncd py-shinywidgets/website/gallery/{kind}/{slug}\n{command}\n```\n"


def test_gallery_run_block_matches(tmp_path: Path) -> None:
    md = gallery_page(
        tmp_path,
        "showcases",
        "x",
        "---\ntitle: X\nrun: uv run --with nibabel shiny run app.py\n---\n\n"
        "Intro.\n\n## Run it\n\n"
        + run_block("showcases", "x", "uv run --with nibabel shiny run app.py"),
    )

    assert check_gallery_run(md) == []


def test_gallery_run_block_matches_template(tmp_path: Path) -> None:
    md = gallery_page(
        tmp_path,
        "templates",
        "y",
        "---\ntitle: Y\nrun: uv run shiny run app.py\n---\n\n"
        "## Run it\n\n" + run_block("templates", "y", "uv run shiny run app.py"),
    )

    assert check_gallery_run(md) == []


def test_gallery_run_block_drift_reported(tmp_path: Path) -> None:
    md = gallery_page(
        tmp_path,
        "showcases",
        "x",
        "---\ntitle: X\nrun: uv run shiny run app.py\n---\n\n"
        "## Run it\n\n"
        + run_block("showcases", "x", "uv run --with nibabel shiny run app.py"),
    )

    problems = check_gallery_run(md)

    assert len(problems) == 1
    assert "does not match" in problems[0]


def test_gallery_run_wrong_cd_reported(tmp_path: Path) -> None:
    md = gallery_page(
        tmp_path,
        "showcases",
        "x",
        "---\ntitle: X\nrun: uv run shiny run app.py\n---\n\n"
        "## Run it\n\n" + run_block("showcases", "other", "uv run shiny run app.py"),
    )

    problems = check_gallery_run(md)

    assert len(problems) == 1
    assert "does not match" in problems[0]


def test_gallery_run_block_missing(tmp_path: Path) -> None:
    md = gallery_page(
        tmp_path,
        "showcases",
        "x",
        "---\ntitle: X\nrun: uv run shiny run app.py\n---\n\nNo block here.\n",
    )

    problems = check_gallery_run(md)

    assert len(problems) == 1
    assert "no ```sh block" in problems[0]


def test_gallery_run_heading_missing(tmp_path: Path) -> None:
    md = gallery_page(
        tmp_path,
        "showcases",
        "x",
        "---\ntitle: X\nrun: uv run shiny run app.py\n---\n\n"
        + run_block("showcases", "x", "uv run shiny run app.py"),
    )

    problems = check_gallery_run(md)

    assert len(problems) == 1
    assert "## Run it" in problems[0]


def test_gallery_run_noop_without_run_front_matter(tmp_path: Path) -> None:
    md = gallery_page(tmp_path, "showcases", "x", "---\ntitle: X\n---\n\nNothing to check.\n")

    assert check_gallery_run(md) == []


def test_slugify_matches_github_style() -> None:
    assert (
        slugify("1. Selection &rarr; table of rows") == "1-selection--table-of-rows"
    )  # GitHub drops the arrow, keeping both spaces
