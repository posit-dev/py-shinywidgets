"""Snippet-drift and dead-link checker for the website's Markdown pages.

Usage: uv run --no-sync python website/_tools/check_docs.py [--snippets] [--links] [PATH...]
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

GUIDE_FILENAMES = {"index.md", "cheatsheet.md"}
WEBSITE = Path(__file__).resolve().parents[1]

FENCE_CLOSE = "```"
FENCE_ATTR = re.compile(r'([\w-]+)="([^"]*)"')

HEADING_PREFIX = "#"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the website's Markdown pages for snippet drift and dead links."
    )
    parser.add_argument(
        "--snippets",
        action="store_true",
        help="only check that python code blocks match their linked examples/ file",
    )
    parser.add_argument(
        "--links",
        action="store_true",
        help="only check that relative links and anchors resolve",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[WEBSITE],
        help="a .md file, or a directory searched recursively for index.md/cheatsheet.md (default: website/)",
    )
    args = parser.parse_args(argv)

    run_both = not args.snippets and not args.links
    run_snippets = args.snippets or run_both
    run_links = args.links or run_both

    problems: list[str] = []
    for md in collect_md_files(args.paths):
        if run_snippets:
            problems.extend(check_snippets(md))
            problems.extend(check_gallery_run(md))
        if run_links:
            problems.extend(check_links(md))

    for problem in problems:
        print(problem)
    return 1 if problems else 0


def check_snippets(md: Path) -> list[str]:
    problems: list[str] = []
    lines = md.read_text().splitlines()
    i = 0
    while i < len(lines):
        fence = parse_fence(lines[i])
        if fence is None:
            i += 1
            continue
        start_line = i + 1
        j = i + 1
        while j < len(lines) and lines[j].strip() != FENCE_CLOSE:
            j += 1
        if fence.lang == "python" and not is_skipped_snippet(lines, start_line):
            problems.extend(
                f"{md}:{start_line}: {p}"
                for p in check_tagged_block(md, fence, lines[i + 1 : j])
            )
        i = j + 1
    return problems


RUN_FRONT_MATTER = re.compile(r"^run:\s*(\S.*?)\s*$", re.M)
FRONT_MATTER = re.compile(r"---\n(.*?)\n---\n", re.S)
CLONE_COMMAND = "git clone --depth 1 https://github.com/posit-dev/py-shinywidgets"


def check_gallery_run(md: Path) -> list[str]:
    """A gallery page (`run:` front matter) must show, under a "## Run it"
    heading, a ```sh block that clones the repo, cds into the page's own
    directory, and runs its `run:` command."""
    text = md.read_text()
    fm = FRONT_MATTER.match(text)
    if fm is None:
        return []
    run = RUN_FRONT_MATTER.search(fm.group(1))
    if run is None:
        return []
    expected = [
        CLONE_COMMAND,
        f"cd py-shinywidgets/website/gallery/{md.parent.parent.name}/{md.parent.name}",
        run.group(1),
    ]
    lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        fence = parse_fence(lines[i])
        if fence is None:
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j].strip() != FENCE_CLOSE:
            j += 1
        if fence.lang == "sh":
            blocks.append((i + 1, lines[i + 1 : j]))
        i = j + 1
    if not blocks:
        return [f"{md}: `run:` front matter but no ```sh block"]
    start_line, block_lines = blocks[0]
    problems = []
    if trim_block(block_lines) != expected:
        problems.append(
            f"{md}:{start_line}: ```sh block does not match clone + cd + run: ({run.group(1)!r})"
        )
    if "## Run it" not in [line.strip() for line in lines[:start_line]]:
        problems.append(f"{md}:{start_line}: ```sh block is not under a `## Run it` heading")
    return problems


@dataclass(frozen=True)
class Fence:
    indent: str
    lang: str
    attrs: dict[str, str]


def parse_fence(line: str) -> Fence | None:
    """Parse an opening ```lang or ```{.lang key="value" ...} fence line."""
    stripped = line.lstrip()
    if not stripped.startswith(FENCE_CLOSE):
        return None
    indent = line[: len(line) - len(stripped)]
    rest = stripped[len(FENCE_CLOSE) :].strip()
    if not rest:
        return None
    if rest.startswith("{") and rest.endswith("}"):
        inner = rest[1:-1].strip()
        lang = inner.split()[0].lstrip(".") if inner else ""
        return Fence(indent, lang, dict(FENCE_ATTR.findall(inner)))
    return Fence(indent, rest, {})


def check_tagged_block(md: Path, fence: Fence, block_lines: list[str]) -> list[str]:
    target = fence.attrs.get("file")
    if target is None:
        return ['untagged snippet (add file="examples/...")']
    problems: list[str] = []
    target_path = resolve_relative(md, target)
    if not target_path.is_file():
        problems.append(f"snippet file missing: {target}")
    elif not block_matches_file(block_lines, target_path.read_text().splitlines()):
        problems.append(f"snippet does not match {target}")
    for extra in fence.attrs.get("files", "").split():
        if not (target_path.parent / extra).is_file():
            problems.append(f"extra file missing: {extra} (next to {target})")
    collapse = fence.attrs.get("collapse")
    if collapse is not None and collapse not in ("true", "false"):
        problems.append(f'collapse must be "true" or "false", not "{collapse}"')
    return problems


def is_skipped_snippet(lines: list[str], start_line: int) -> bool:
    # A block that is a made-up inline illustration (not from an examples/ file)
    # is marked with <!-- snippet: skip --> on the line just before its fence.
    idx = start_line - 2
    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    return idx >= 0 and lines[idx].strip() == "<!-- snippet: skip -->"


def block_matches_file(block_lines: list[str], file_lines: list[str]) -> bool:
    block = trim_block(block_lines)
    if not block:
        return False
    if block == trim_block(file_lines):
        return True
    # A snippet may be a verbatim excerpt: a contiguous run of the file's
    # lines, possibly with its original indentation removed.
    block = dedent_lines(block)
    n = len(block)
    file_lines = [line.rstrip() for line in file_lines]
    for start in range(len(file_lines) - n + 1):
        if dedent_lines(file_lines[start : start + n]) == block:
            return True
    return False


def trim_block(lines: list[str]) -> list[str]:
    trimmed = [line.rstrip() for line in lines]
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    return trimmed


def dedent_lines(lines: list[str]) -> list[str]:
    indent = min(
        (len(line) - len(line.lstrip()) for line in lines if line.strip()),
        default=0,
    )
    if indent == 0:
        return lines
    return [line[indent:] if line.strip() else "" for line in lines]


def check_links(md: Path) -> list[str]:
    problems: list[str] = []
    lines = md.read_text().splitlines()
    slugs_by_file: dict[Path, set[str]] = {}
    for lineno, line in enumerate(lines, start=1):
        for target in find_links(line):
            if is_absolute_url(target):
                continue
            path_part, _, fragment = target.partition("#")
            target_path = (md.parent / path_part).resolve() if path_part else md
            if path_part and not target_path.exists():
                problems.append(f"{md}:{lineno}: missing link target: {target}")
                continue
            if fragment and target_path.suffix == ".md":
                if target_path not in slugs_by_file:
                    slugs_by_file[target_path] = extract_slugs(target_path)
                if fragment not in slugs_by_file[target_path]:
                    problems.append(
                        f"{md}:{lineno}: unresolved anchor #{fragment} in {target}"
                    )
    return problems


def slugify(heading: str) -> str:
    # GitHub-style slugs: lowercase, drop punctuation other than - and _,
    # then turn each space into a hyphen (runs of spaces become runs of
    # hyphens, e.g. "Click -> detail card" -> "click---detail-card").
    text = drop_entities(heading)
    text = text.lower()
    text = "".join(c for c in text if c.isalnum() or c in " _-")
    return text.strip().replace(" ", "-")


def collect_md_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            for name in GUIDE_FILENAMES:
                files.extend(path.rglob(name))
        else:
            files.append(path)
    return sorted(set(files), key=str)


def find_links(line: str) -> list[str]:
    targets: list[str] = []
    i = 0
    while True:
        start = line.find("[", i)
        if start == -1:
            break
        close_bracket = line.find("]", start)
        if (
            close_bracket == -1
            or close_bracket + 1 >= len(line)
            or line[close_bracket + 1] != "("
        ):
            i = start + 1
            continue
        close_paren = line.find(")", close_bracket + 2)
        if close_paren == -1:
            i = start + 1
            continue
        targets.append(line[close_bracket + 2 : close_paren])
        i = close_paren + 1
    return targets


def is_absolute_url(target: str) -> bool:
    scheme, sep, _ = target.partition(":")
    return (
        bool(sep)
        and scheme.replace("+", "").replace("-", "").replace(".", "").isalnum()
    )


def resolve_relative(md: Path, target: str) -> Path:
    return (md.parent / target.split("#", 1)[0]).resolve()


def extract_slugs(md: Path) -> set[str]:
    slugs: set[str] = set()
    for line in md.read_text().splitlines():
        stripped = line.lstrip()
        if not stripped.startswith(HEADING_PREFIX):
            continue
        rest = stripped.lstrip(HEADING_PREFIX)
        if not rest.startswith(" "):
            continue
        slugs.add(slugify(rest.strip()))
    return slugs


def drop_entities(text: str) -> str:
    result: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "&":
            end = text.find(";", i + 1)
            if end != -1 and end - i <= 10:
                i = end + 1
                continue
        result.append(text[i])
        i += 1
    return "".join(result)


def normalize_block(lines: list[str]) -> str:
    return "\n".join(line.rstrip() for line in lines).rstrip("\n")


if __name__ == "__main__":
    sys.exit(main())
