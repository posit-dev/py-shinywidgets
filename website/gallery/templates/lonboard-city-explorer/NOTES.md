# Verification notes

- Source: promoted from `docs/widget-guides/lonboard/gallery/template_city_explorer.py`. Header
  reformatted to the gallery convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. Several real clicks on the WebGL canvas (`img/after.webp`) landed on a city dot and
  produced "Kigali, Rwanda, Population: 860,000" in the Detail tab. Did not separately re-drive the
  box-select tool in this pass (already gesture-verified in `lonboard/NOTES.md`); the click-to-detail
  path, this template's headline gesture, was independently re-verified here.
- No new shinywidgets bugs found.
