# Verification notes

- Source: promoted from `docs/widget-guides/ipydatagrid/gallery/template_spreadsheet.py`. Header
  reformatted to the gallery convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. A real drag-select over a 2x2 block of cells (`img/after.webp`): status bar showed "Count
  8 . Sum 513" and "Average 64.1 . Min 44 . Max 97", matching the visible grid values.
- Did not separately re-drive `edited_cell()` with a double-click + keystroke in this pass (covered
  already in `ipydatagrid/NOTES.md`'s gesture-verified accessor table); the cell-selection drag,
  the template's primary pattern, was independently re-verified here.
- Carries the known `selected()` rate-policy limitation noted in the ipydatagrid guide (see
  README "Known limitation").
