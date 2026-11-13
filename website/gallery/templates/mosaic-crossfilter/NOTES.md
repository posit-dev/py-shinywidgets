# Verification notes

- Source: promoted from
  `docs/widget-guides/mosaic/gallery/template_crossfilter_starter.py`. Header reformatted to the
  gallery convention, plus an added caveat paragraph about the pending DuckDB lockdown (see
  below); no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. A real drag-brush over the scatter plot (`img/after.webp`): "27 of 342 selected", the
  histogram's blue (filtered) bars correctly subset the gray (context) bars, and the per-species
  table showed Adelie 23 / Chinstrap 3 / Gentoo 1, consistent with the brushed region.
- Caveat carried from `docs/widget-guides/FINDINGS.md` ("quak (and mosaic): SECURITY"):
  `render_mosaic_widget` does not lock down its DuckDB connection against browser-sent SQL on
  current `main` (fix on local branch `fix/duckdb-lockdown-quak-mosaic`, not merged). Noted in this
  template's README front matter per the gallery assignment's instruction to disclose dependencies
  on release-blocking caveats. This template's own connection only touches the bundled penguins
  CSV, so the practical risk here is low, but it's worth the maintainer's attention before this
  page goes live if the fix hasn't landed yet.

## Update 2026-11-11 (main @ 32ca7035)

- **Caveat resolved**: PR #395 (quak/mosaic DuckDB lockdown) merged -- `render_mosaic_widget`
  now locks its connection down by default (`SET enable_external_access = false`), with
  `allow_unrestricted_connection=True` as an explicit opt-out. Removed the "pending PR #395"
  caveat from the app.py header comment and the README's "Dependency note" section; this
  template never needed the opt-out (it only queries the bundled penguins DataFrame).
- Re-verified with Playwright: a real drag-brush over the scatter plot's blue/orange cluster
  gave "180 of 342 selected" with Adelie (132, mean 3701g) and Chinstrap (48, mean 3623g) in the
  table, and the histogram's blue (filtered) bars correctly subset the gray (context) bars --
  `img/after_brush.webp`. No console/server errors; the lockdown is transparent to this template's
  own usage.
- `dashboard.data(filter_by=...)` (#403, new this pass) wasn't adopted here: the template's
  `dashboard.data()` call (no `table`/`filter_by` args) already filters by every active selection,
  which is exactly what this crossfilter wants -- `filter_by` only matters for apps with multiple
  independent selections, which this template deliberately doesn't have (YAGNI).
- Accessors: `dashboard.params()`, `dashboard.data()` -- both verified with a real gesture
  (brush), consistent with the 2026-11-02 pass's verification approach.
