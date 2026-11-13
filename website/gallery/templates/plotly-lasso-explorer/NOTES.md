# Verification notes

- Source: promoted from `docs/widget-guides/plotly/gallery/template_lasso_explorer.py` (already a
  verified gallery candidate in the plotly guide). Header reformatted to the gallery's
  title/summary/bucket/widgets/pattern/run/data convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. Hero screenshot (`img/hero.webp`) plus a real lasso-drag gesture via Playwright
  (`img/after.webp`): 38 of 142 rows selected, table and summary both updated correctly.
- No new shinywidgets bugs found. See `plotly/NOTES.md` for the full accessor verification history
  (`clicked()`/`selected_rows()` docstring caveats already documented there).
