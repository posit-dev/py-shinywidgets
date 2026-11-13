# Verification notes

- Source: promoted from `docs/widget-guides/ipycytoscape/gallery/template_network_explorer.py`.
  Header converted from a `__doc__ = """..."""` assignment to a `#` comment block, matching the
  gallery convention used everywhere else in this directory (both avoid Shiny Express rendering
  the header as page text); no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync shiny run app.py`, port
  10081. A real click at the canvas center (`img/after.webp`) landed on node "33", showing its 17
  neighbors and turning it red in the graph.
- No new shinywidgets bugs found; see `ipycytoscape/NOTES.md` for the full accessor verification
  history (the `rate_policy`/`rate_delay` near-no-op caveat already documented there).

## Update 2026-11-11 (main @ 32ca7035)

- **Bug fixed**: since #437, `clicked_node()`'s payload is kept across a re-render instead of
  resetting to `None`. Switching the Graph dropdown re-renders `network` with a different graph,
  so a stale click from the old graph survived into `detail()`'s `next(n for n in g.nodes if
  str(n) == clicked["data"]["id"])` with no default -- `StopIteration` (an uncaught 500) the
  moment that node id didn't exist in the new graph. Fixed with `next(..., None)` plus an explicit
  `None` check; verified with Playwright: click a karate-club node (`cyto_tpl_02_after_click.webp`
  equivalent -> neighbor list for node 32), then switch to Les Misérables -- no crash, sidebar
  cleanly falls back to the placeholder (`img/after_switch_graph.webp`). Server log confirmed no
  traceback either side of the switch.
- `clicked_node()` was already using the current (#441) name; no rename needed here.
- Accessors: `clicked_node()` -- verified with a real gesture (click + graph switch), both
  outcomes screenshotted and read.
