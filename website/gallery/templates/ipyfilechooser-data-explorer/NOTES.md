# Verification notes

- Source: promoted from
  `docs/widget-guides/ipyfilechooser/gallery/template_data_explorer.py`. Header reformatted to the
  gallery convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. Real two-click gesture (open dialog, select `tips.csv` from the directory listing, confirm)
  per `tests/playwright/render_ipyfilechooser/test_render_ipyfilechooser.py`'s documented flow
  (`img/after.webp`): table showed the tips data (244 rows) and the plot correctly branched to the
  histogram (`total_bill` by `sex`), confirming the column-based branching logic.
- No new shinywidgets bugs found; see `ipyfilechooser/NOTES.md` for the `.reset(path=...)` upstream
  callback-skip caveat (not exercised by this template).
