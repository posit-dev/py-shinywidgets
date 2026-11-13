# Verification notes

- Source: promoted from `docs/widget-guides/mols2grid/gallery/template_grid_explorer.py`. Header
  reformatted to the gallery convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. mols2grid renders inside an iframe; checkbox clicks had to target `.m2g-cell` (the input
  itself is visually hidden), per `tests/playwright/mols2grid_accessors/test_mols2grid_accessors.py`.
  Checked 3 cells via Playwright (`img/after.webp`): all 3 appeared correctly in the "Selected
  molecules" table with matching SMILES/ID/LogS.
- No new shinywidgets bugs found; see `mols2grid/NOTES.md` for the full accessor verification
  history.
