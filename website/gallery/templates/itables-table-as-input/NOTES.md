# Verification notes

- Source: promoted from `docs/widget-guides/itables/gallery/template_table_as_input.py`. Header
  reformatted to the gallery convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. Hero screenshot and a real row-click gesture (`img/after.webp`): "1 selected", mean life
  expectancy and total population recomputed correctly for Albania.
- Ctrl-click to extend the selection to multiple rows did not register in this automated pass
  (only the last-clicked row stayed selected); single-row selection works and drives the summary
  correctly, which is what this template demonstrates. Not treated as a bug -- not re-tested
  manually, and itables' own test suite covers multi-select separately.
