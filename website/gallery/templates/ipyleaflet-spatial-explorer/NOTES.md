# Verification notes

- Source: promoted from `docs/widget-guides/ipyleaflet/gallery/template_spatial_explorer.py`.
  Header reformatted to the gallery convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. A real click at the map's center (`img/after.webp`): "Pod #204, 1337 car-hours" displayed,
  "In view" read 249/249 (the full dataset, matching the unpanned/unzoomed viewport).
- No new shinywidgets bugs found; see `ipyleaflet/NOTES.md` for the full accessor verification
  history (`clicked()` dedupe-on-dblclick docstring caveat already documented there).
