# Verification notes

- Source: promoted from
  `docs/widget-guides/articles/linked-views/examples/06_ipyleaflet_bounds_to_plotly.py` (credited
  in the article's own `NOTES.md` as "reused, boot-tested" from the ipyleaflet guide). Added a `#`
  comment header (title/summary/bucket/widgets/pattern/run/data), `full_screen=True` on both cards,
  and card headers; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081.
  - A small pan (one drag) changed the map only slightly and left the chart counts unchanged
    (expected: all markers were still in view) -- not used as the final screenshot since it doesn't
    visibly demonstrate the pattern.
  - A double-click zoom (3x) on the dense cluster produced a clearly different viewport and a
    clearly different chart (`img/after.webp`: night 127->22, morning 38->7, afternoon 33->0,
    evening 51->5), a better demonstration of "viewport drives chart" than a same-view pan.
- No new shinywidgets bugs found.
