# website/_tools

Scripts that test the website, plus `sync_landing_counts.py`, which `make docs` runs before rendering.

## sync_landing_counts.py
`uv run --no-sync python website/_tools/sync_landing_counts.py`
Rewrites the landing page's category-card counts (`<span class="n">` in `index.qmd`) from the Widgets
sidebar groups in `_quarto.yml`, the source of truth for which guides belong to which category. Fails if a
sidebar group has no card or a card names no group. Run automatically by `make docs`. `check_docs.py` and `smoke.py` stand in for unit tests on the page
content; `check_site.py` checks the rendered site in a browser (`make docs-check`).

## check_docs.py
`uv run --no-sync python website/_tools/check_docs.py [--snippets] [--links] [PATH...]`
`PATH` is a `.md` file, or a directory searched recursively for `index.md`/`cheatsheet.md` (default: `website/`).
`--snippets` checks every fenced ` ```python ` block against the file named by its `file=` attribute
(` ```{.python file="examples/x.py"} `); a block without one is an `untagged snippet`. `files="a.py b.js"`
entries (extra files the example needs, relative to its directory) must exist, and `collapse` must be
`"true"` or `"false"`.
A block passes if it equals the whole file *or* a contiguous run of the file's lines (an excerpt), in each
case ignoring common leading indentation and trailing blank lines. A block that is a made-up inline
illustration, not from any file, is exempt when `<!-- snippet: skip -->` appears on the line just before its
fence. Anchors are slugified GitHub-style: lowercase, punctuation other than `-`/`_` dropped, each space
turned into a hyphen (so `Click -> detail card` is `#click---detail-card`).
`--links` checks relative link targets exist and `#fragment`s resolve to a heading. Neither flag runs both.
Prints `file:line: message` per problem, exits 1 if any. `BASELINE.txt` (empty) records known problems; the
site must stay at zero.

## smoke.py
`uv run --no-sync python website/_tools/smoke.py APP.py [--shot OUT.webp] [--gpu {none,webgl,webgpu}] [--wait SELECTOR]`
Runs `APP.py` on a free port, loads it in headless Chromium, fails (exit 1) on a server traceback, a
server-log `ERROR` line, a shinywidgets logger exception (`ClientMsgErrorFilter`'s "Exception in widget
method" -- catches a widget that raises asynchronously after `--wait`'s selector already matched), an
uncaught page error, or a 60s timeout waiting for a rendered widget.

## check_site.py
`uv run --no-sync python website/_tools/check_site.py [--only NAME ...]` (or `make docs-check`)
Serves the built site (`website/_site`) under `/py-shinywidgets/`, as GitHub Pages will, so a root-absolute
URL shows up as a 404. Each `@check("name")` gets a fresh browser page; every check also fails on any HTTP
status >= 400, failed request, or uncaught page error. Checks cover the theme, the Guide sidebar, every
sidebar page, in-site `#anchors`, the reference, the gallery, the changelog, example-block headers
(collapse, copy, and the Shinylive URL, with shinylive.io stubbed), and the landing page (tabs,
stage, reduced motion, phone width, and the always-dark landing vs. the reader's docs theme).

## make_landing_images.py
`uv run --no-sync python website/_tools/make_landing_images.py [--check]`
Cuts the landing page's images (`website/assets/landing/img/`) from screenshots the site's pages already
show, with crop boxes as fractions of each source. `--check` fails if the images exceed 4 MB or if the
landing page uses an image that doesn't exist.

## Tests
`cd website/_tools && uv run --no-sync python -m pytest -q` runs the unit tests for `check_docs.py` and the
reference renderer's role resolver (`website/_renderer.py`), and renders
`fixtures/example_header/` through the example-header filter (`test_example_header.py`; skipped without Quarto).
