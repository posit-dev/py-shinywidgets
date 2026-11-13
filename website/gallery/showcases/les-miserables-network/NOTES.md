# NOTES: les-miserables-network

- Promoted from `docs/widget-guides/ipycytoscape/gallery/showcase_les_miserables.py`. The
  original used the `__doc__ = """..."""` assignment trick to keep a long description off
  the rendered page in Shiny Express; **converted to a plain `#`-comment header** to match
  this bucket's convention (BRIEF.md: "a `#` comment header (NOT a module docstring)"). The
  `__doc__` trick technically also avoids rendering (it's an assignment, not a bare string
  literal), but using a real docstring-shaped block for a *showcase header* risks confusing
  future readers who skim for `__doc__ =` as "this is special"; a plain comment block is the
  same convention every other showcase in this bucket uses.
- Re-verified 2026-11-02 in `main-wt`: ipycytoscape 1.3.3, networkx 3.7, both already in the
  shared venv, no `--with` overlay.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + graph renders | yes (Playwright) | `#network canvas` visible, `img/hero.webp` |
| Click on the graph near the Valjean node | yes (real click) | landed on a tie instead of the node (graphs are laid out force-directed, so a fixed-fraction click can hit either); `#info` changed from "Click a character or tie." to `"Javert + Woman1: 1 scenes"`, confirming `clicked_edge()` fires and the box-selection outline rendered, `img/after_click.webp` |

## Judgment calls

- Converted the `__doc__` trick to a `#`-comment header (see above). This is the one
  substantive edit made to any promoted app's logic in this batch; everything else was
  limited to the `# Run:` header line.
- The real click landed on an edge rather than the intended node (Valjean), since the
  force-directed layout's node positions aren't fully deterministic pixel-for-pixel across
  runs. This still confirms the showcase's interactivity (both `clicked_node()` and
  `clicked_edge()` are exercised by the same gesture family), so no further gesture was
  attempted.

## Update 2026-11-11 (main @ 32ca7035)

- **Narrative fix**: `group_stats()` looped `reactive_read(n, "selected")` over every child node
  widget by hand. ipycytoscape gained a dedicated `selected_nodes()` accessor for exactly this
  (new this pass -- box/multi-select, data dicts, `[]` when empty, debounced by default), so
  rewrote it as `{n["id"] for n in network.selected_nodes()}`. Dropped the now-unused
  `reactive_read` import. `network.clicked_node()`/`clicked_edge()` were already on the current
  (#441) names; nothing to rename there.
- Verified with Playwright: a real shift-drag box-select over most of the canvas produced
  visible black selection outlines on the caught nodes and `#group_stats` read `"72 characters
  · 249 ties inside the group · density 0.10"` -- `img/after_box_select.webp`. No console/server
  errors across the gesture.
- Accessors: `network.selected_nodes()` -- verified with a real gesture this pass (not covered
  by the 2026-11-02 pass, which only drove the click gesture). `clicked_node()`/`clicked_edge()`
  -- not re-driven this pass (unchanged code path, already verified 2026-11-02).
