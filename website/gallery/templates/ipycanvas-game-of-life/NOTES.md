# Verification notes

- Source: promoted from `docs/widget-guides/ipycanvas/gallery/template_game_of_life.py`. Header
  reformatted to the gallery convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. Seeded a small pattern via 5 real clicks (`img/before.webp`: "Generation: 0", pattern
  visible), then clicked "Play / pause" and waited ~2.5s (`img/after.webp`: "Generation: 21", the
  pattern had evolved/moved).
- No new shinywidgets bugs found; see `ipycanvas/NOTES.md` for the `hold_canvas()` no-op finding
  (not exercised by this template, which draws a full frame per tick) and the unverified
  core-Shiny flake noted there (not reproduced in this pass).
