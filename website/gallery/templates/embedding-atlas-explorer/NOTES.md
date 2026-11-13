# Verification notes

- Source: promoted from `docs/widget-guides/embedding-atlas/gallery/template_atlas_explorer.py`.
  Header reformatted to the gallery convention; data path changed from
  `Path(__file__).parent.parent / "examples" / "data" / "issues.parquet"` (guide-directory
  relative) to `Path(__file__).parent / "data" / "issues.parquet"`, with the parquet file (3 MB)
  copied alongside the template so it is self-contained. No other logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081, Chromium launched `channel="chromium"` with
  `args=["--enable-unsafe-webgpu", "--use-angle=metal"]` and loaded from `http://127.0.0.1:<port>`
  (WebGPU needs a secure-context origin), per `embedding-atlas/NOTES.md`.
- First drag attempt (plain mouse drag) panned the view instead of brushing (unchanged
  "6,088 / 6,088 points", `img/hero.webp`-equivalent). Clicking the box-select icon in the canvas
  toolbar first, then dragging, produced a real brush (`img/after.webp`): 1,764 of 6,088 rows
  selected, repo/language/state breakdowns and the detail table all updated consistently with the
  brushed region.
- No new shinywidgets bugs found.
