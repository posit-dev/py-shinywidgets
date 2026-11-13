# NOTES: stdlib-import-graph

- Promoted from `docs/widget-guides/ipysigma/gallery/showcase_stdlib_imports.py`, unchanged
  except the `# Run:` header line.
- Re-verified 2026-11-02 in `main-wt`: ipysigma 0.24.6, networkx 3.7 (both already in the
  shared venv; `nx.community.louvain_communities`/`nx.forceatlas2_layout` both present on
  this networkx version). No `--with` overlay needed.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + graph renders | yes (Playwright) | `#graph canvas` visible, `img/hero.webp` |
| `page.select_option("#focus", ...)` on the underlying `<select>` | attempted, failed | selectize.js hides the original `<select>`; not a shinywidgets issue, a standard Playwright-vs-selectize interaction quirk also hit in two other promoted showcases this pass |
| Real click on the "os" node (`#graph canvas`) | yes | `#summary` changed from `"import asyncio"` (imports 27, imported by 1) to `"import os"` (imports 0, imported by 28), `img/after_select.webp` |

## Judgment calls

- Switched the planned gesture from "select a module via the sidebar dropdown" to "click a
  node directly on the sigma canvas" after the selectize-hidden-`<select>` issue (same root
  cause documented in `les-miserables-network/NOTES.md`). The canvas click exercises the
  *reverse* direction of the same two-way sync (`selected_node` -> `.read()` ->
  sidebar), which is at least as strong a confirmation of the accessor.

## Update 2026-11-11 (main @ 32ca7035)

- **Narrative fix**: both `reactive_read(graph.widget, "camera_state")` and
  `reactive_read(graph.widget, "selected_node")` converted to `graph.read("camera_state")` /
  `graph.read("selected_node")` (tier 2 -- the taught fallback for a renderer output's bare
  synced traits). Dropped the now-redundant `req(graph.widget)` guards in `_track_camera` and
  `_select_to_focus`: `.read()` already cancels (like `req(False)`) before the output's first
  render, via `self.widget`'s own reactive cancel. Dropped the unused `req` import.
  `ipysigma` still has no dedicated accessors of its own (confirmed in
  `shinywidgets/_render_widget.py`), so this is purely the fallback-tier rename, not a new
  accessor.
- Verified with Playwright: clicked the "logging" node directly -- sidebar synced to `"import
  logging"` (24 imports, 5 importers) matching the graph recolor (`img/after_node_click.webp`);
  no console/server errors across several clicks (each one re-renders `graph` and re-runs both
  converted effects, so `camera_state`'s round trip was exercised repeatedly, not just once).
- Accessors: `graph.read("selected_node")`, `graph.read("camera_state")` -- both verified with a
  real gesture (node clicks), consistent with the 2026-11-02 verification's figures style.
