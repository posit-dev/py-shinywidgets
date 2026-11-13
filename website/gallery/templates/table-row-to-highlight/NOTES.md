# Verification notes

- Source: promoted from
  `docs/widget-guides/articles/linked-views/examples/09_itables_selection_to_plotly_inplace.py`
  (credited in the article's own `NOTES.md` as "reused, boot-tested" from the itables guide). Added
  a `#` comment header (title/summary/bucket/widgets/pattern/run/data); no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. Selected the first table row via Playwright click (`img/after.webp`): the Afghanistan
  point turned red in the scatter plot (bottom-left, matching its low GDP/life-expectancy values),
  confirming the in-place color-array highlight.
- No new shinywidgets bugs found.
