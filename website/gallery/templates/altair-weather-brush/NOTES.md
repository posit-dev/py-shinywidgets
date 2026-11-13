# Verification notes

- Source: promoted from `docs/widget-guides/altair/gallery/template_weather_brush.py`. Header
  reformatted to the gallery convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync --with vega_datasets
  shiny run app.py`, port 10081. Hero screenshot before any interaction (`img/hero.webp`, "Days
  selected: 0") and a real left-to-right drag on the chart's `<svg>` (`img/after.webp`: 483 days
  selected, average high 15.0degC, table populated).
- Judgment call: the altair guide's review-pass TODO suggests `altair.datasets` may replace
  `vega_datasets` going forward; left as `vega_datasets` here to match the still-current guide.
  [Resolved 2026-11-02, maintainer Decision 8: switched to `from altair.datasets import data`
  (bundled with altair 6.3.0; same upstream vega-datasets file), run command is now plain
  `uv run --no-sync shiny run app.py`. Screenshots unchanged -- the data is byte-identical.]
