# Verification notes

- Source: promoted from `docs/widget-guides/jscatter/gallery/template_linked_scatter.py`. Header
  converted from a `__doc__ = """..."""` assignment to a `#` comment block, matching the gallery
  convention used everywhere else in this directory; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. A real long-press-then-drag lasso on the first plot (per
  `tests/playwright/jscatter_accessors/test_jscatter_accessors.py`'s documented gesture)
  (`img/after.webp`): both plots show the matching points outlined, and the table reports "2,485 of
  5,000 cars selected".
- No new shinywidgets bugs found; see `jscatter/NOTES.md` for the full accessor verification
  history.
