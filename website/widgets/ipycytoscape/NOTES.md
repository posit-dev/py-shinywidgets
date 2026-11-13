# NOTES: ipycytoscape guide

## Versions and environment

- Date: 2026-10-30
- shinywidgets: `main` @ `00f90249` (read from the main checkout at
  `/Users/cpsievert/github/py-shinywidgets`; `uv run` commands were executed from an isolated worktree at the same
  commit, `/private/tmp/claude-502/-Users-cpsievert-github-py-shinywidgets/b5f9c833-cf3f-448f-841f-2c46c3116629/scratchpad/main-wt`,
  after the coordinator flagged that another session was switching branches in the main checkout mid-pass)
- shiny 1.9.0, ipycytoscape 1.3.3 (bundles cytoscape.js core plus the `cola`, `dagre`, and `klay` layout
  extensions), networkx 3.7, pandas (whatever `uv.lock` pins; used only for `nx.from_pandas_edgelist`)
- `shinywidgets/_cytoscape.py` and the `render_ipycytoscape` section of `_render_widget.py` are byte-identical
  between the main checkout and the worktree, so nothing in this guide depends on commits after `00f90249`.
- Playwright Chromium, headless, launched with `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist` (canvas-based widget; flags kept for parity with the old report, though this environment
  renders canvases fine by default too). Screenshots: 1280x800 viewport, `device_scale_factor=2`.
- Ports 9400-9419 (assigned range; actually used only 9401 locally since each example app was launched, screenshot,
  and torn down sequentially rather than run concurrently).
- Driver script: `/private/tmp/claude-502/-Users-cpsievert-github-py-shinywidgets/b5f9c833-cf3f-448f-841f-2c46c3116629/scratchpad/agents/ipycytoscape/driver.py`

## Verification table

Every example and gallery app was launched with `shiny.run.run_shiny_app`, driven with Playwright, and
screenshotted; every screenshot was viewed with the Read tool before being referenced in `guide.md`.

| file | ran | screenshot(s) | gesture driven | accessor/claim confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | `quickstart.webp` | none (static) | n/a |
| `examples/02_data_driven_style.py` | yes | `data_driven_style.webp` | none (static) | data-driven size/width via `mapData` |
| `examples/03_pandas_edgelist.py` | yes | `pandas_edgelist.webp` | none (static) | `from_pandas_edgelist` + directed arrows |
| `examples/04_layouts.py` | yes | `layouts_cose.webp`, `layouts_dagre.webp`, `layouts_concentric.webp`, `layouts_breadthfirst.webp` | layout dropdown x3 | cola/dagre/klay extensions all render (dagre shown in guide; concentric/breadthfirst screenshots kept as extra evidence, not inlined) |
| `examples/05_tooltips.py` | yes | `tooltips_before.webp`, `tooltips_after.webp` | click (precise: concentric layout puts the target node at canvas center) | tooltip text and line break confirmed in the browser |
| `examples/06_clicked_node.py` | yes | `node_clicked_before.webp`, `node_clicked_after.webp` | click (canvas center, concentric layout) | `clicked_node()` confirmed: detail card shows member 33's data |
| `examples/07_clicked_edge.py` | yes | `edge_clicked_before.webp`, `edge_clicked_after.webp` | click (exact midpoint computed from the live `cytoscape_obj`'s `renderedPosition()`, via the `expose_manager` route) | `clicked_edge()` confirmed: "Valjean and Cosette share 31 scenes" |
| `examples/08_selection_reactive_read.py` | yes | `selection_before.webp`, `selection_after.webp` | shift-drag box select | `reactive_read(node, "selected")` confirmed: 13 characters, 15 ties, density 0.19, matching the visually selected (red) cluster |
| `examples/09_inplace_vs_rerender.py` | yes | `inplace_zoomed.webp`, `inplace_after_highlight.webp`, `inplace_after_rerender.webp` | scroll-zoom (real gesture) + a precise `cy.zoom()` set for a reproducible screenshot + 2 button clicks | zoom preserved exactly (`2.2` before and after the in-place highlight) vs. reset (`~0.7`, the default fit) after re-render; confirmed via `cytoscape_obj.zoom()` read through the exposed widget manager, not just visually |
| `examples/10_click_neighborhood_highlight.py` | yes | `neighborhood_before.webp`, `neighborhood_after.webp` | click (canvas center, concentric layout) | `clicked_node()` drives in-place class restyle: "Valjean and 36 co-characters are highlighted" |
| `examples/11_shortest_path.py` | yes | `path_before.webp`, `path_after.webp` | selectize dual-pick (Champtercier, Grantaire) | `nx.shortest_path` + in-place class restyle: 5-node path drawn correctly |
| `examples/12_filter_preserve_layout.py` | yes | `filter_before.webp`, `filter_after.webp` | slider drag (via `.irs-handle` + arrow keys) | filtering confirmed both visually and by comparing `renderedPosition()` for all 77 nodes before/after: **0 moved** |
| `gallery/template_network_explorer.py` | yes | `gallery_template_before.webp`, `gallery_template_after.webp` | click (canvas center, concentric layout) | `clicked_node()` confirmed on the template's own graph/layout selectors |
| `gallery/showcase_les_miserables.py` | yes | `gallery_showcase_initial.webp`, `gallery_showcase_click.webp`, `gallery_showcase_select.webp`, `gallery_showcase_path.webp` | click, shift-drag box select, 2x selectize pick | `clicked_node()` (focus+detail card), `clicked_edge()` (wired but not separately screenshotted -- same code path as `examples/07`), `reactive_read` selection (group stats), shortest path, Louvain communities, degree-based sizing all confirmed in one app |

**Accessor coverage: both of this renderer's accessors (`clicked_node()`, `clicked_edge()`) were exercised with a
real browser click and confirmed end-to-end** (Python-side value rendered to a `@render.ui` output and
screenshotted). This is complete coverage for this renderer -- it has exactly two accessors, both covered.

### Methodology notes specific to this widget

- **cose (and cola) layouts are non-deterministic** (randomized initial positions, physics settle over ~1-4
  seconds). Every example that needs a reliable click target for Playwright automation uses `concentric` (puts the
  single highest-degree node dead center) or `preset` with explicit positions instead. This is purely a
  screenshot-determinism concern, not a guide claim -- `cose` is still the default recommended for exploration in
  prose, and is used in every example that doesn't need a scripted click.
- **Verifying the in-place-vs-rerender zoom claim required correcting my own methodology mid-pass.** My first
  attempt set a zoom level via the exposed `cytoscape_obj` immediately after the canvas appeared, then toggled
  classes and found the zoom reset -- which looked like a bug in the "in-place preserves zoom" claim. The actual
  cause: `cose`'s layout animation keeps calling `fit()` internally for several seconds while it settles, so
  setting zoom during that window gets silently overwritten by the *layout's own* next fit, with nothing to do
  with the subsequent class change. Waiting ~4s for the layout to settle before setting zoom reproduced the
  expected result cleanly (zoom held exactly through the in-place update, reset only on re-render). Flagging this
  because it's a trap worth knowing about if anyone re-verifies this guide's claims later.
- **The "filter preserves layout" claim is verified by exact position comparison, not eyeballing.** Screenshots
  alone weren't trustworthy evidence here (a before/after pair can look different-but-equivalent, or
  same-but-actually-moved, depending on what's visible). I added a `renderedPosition()` comparison for every node
  via the exposed `window.widgetManager`, which gives a hard zero-pixels-moved number.

## Bugs and surprises found

1. **[sw, fixed] The old report's height="auto" regression (S3) is fixed on `main`.** The old PR-review report
   (`docs/widget-reports/ipycytoscape/report.md`) found `output_widget(height="auto")` collapsing the graph to
   0px. Current `main`'s CSS (`shinywidgets/static/shinywidgets.css`, the `.__________cytoscape_container` rule)
   explicitly excludes `auto`/`fit-content`/`max-content` keyword heights from the 100%-height override, and this
   is covered by `tests/playwright/render_ipycytoscape_fill::test_cytoscape_keeps_default_height_for_intrinsic_output_height`.
   Not re-verified independently in this pass beyond reading the CSS and the existing test, since it's already a
   committed regression test rather than an open question.
2. **[docs, judgment call worth a second opinion] `render_ipycytoscape`'s `rate_policy`/`rate_delay` kwargs are
   real but close to a no-op for this renderer.** Verified directly (see `check_rate_policy.py` approach below):
   `register_rate_policy()` is called only on the top-level `CytoscapeWidget` the renderer returns, keyed by
   `id(widget)`. The per-node traits worth reading (`selected`, `grabbed`) live on *child* `Node`/`Edge` widgets,
   which never get an entry in `RATE_POLICIES`, so `rate_policy_for(node)` is always `None` regardless of what the
   decorator's kwargs say. I wrote this up explicitly in the "Rate limiting" section rather than silently
   dropping it, since it's a real (if narrow) documentation gap: a user who sets `rate_policy="debounce"` expecting
   it to smooth out box-select floods would see no effect. Repro:
   ```python
   r = render_ipycytoscape(rate_policy="debounce", rate_delay=0.5)
   # ... construct + attach widget, register_rate_policy(widget, ...) ...
   rate_policy_for(widget)  # WidgetRate(...)
   rate_policy_for(node_child)  # None
   ```
3. **[up, pre-existing, re-confirmed] Several upstream ipycytoscape bugs from the old report are still present in
   1.3.3 and still open upstream**: removing a node corrupts the graph (`remove_node_by_id`), `node.selected`
   writes toggle selectability instead of selection, and an invalid `widget.on()` event name corrupts the callback
   registry and ends the Shiny session if hit from inside an effect. I re-verified two of these directly this pass
   (the selectability-swap bug, needed for the selection example; and the Python-to-browser `zoom` trait having no
   effect -- confirmed fresh by setting `network.widget.zoom = 3.0` from a button click and reading
   `cytoscape_obj.zoom()` back through the exposed widget manager: unchanged) and took the node-removal and
   invalid-event-name findings from the old report's forensic work (F3, F9) without re-reproducing them myself,
   since they're unrelated to the accessor/layout surface this pass otherwise covers end-to-end.
4. **[docs, minor] The `render_ipycytoscape` class docstring already correctly documents the eager-attach
   requirement and the `selected`/`selectable` gotcha** (this was a should-fix item in the old PR review; it's
   since been addressed in the shipped docstring). Nothing to flag here beyond confirming it matches what I found
   in the browser.

## Judgment calls

- **Used `nx.les_miserables_graph()` as the primary dataset** (not `karate_club_graph()`) for most examples,
  switching to karate club only for the two simplest ones (quickstart, `clicked_node()`) where a smaller,
  very-well-known graph made the screenshot cleaner. Les Mis gives richer co-appearance weights and named
  communities for the styling/path/showcase examples, matching the brief's suggestion and the old report's gallery
  choice.
- **Chose not to port the old report's F10 "selection-sync throughput" benchmark numbers** (1000/3000-node timing
  tables) into this guide. They're real and still presumably accurate (the underlying mechanism -- one comm
  message per node per flush -- hasn't changed), but re-measuring exact timings felt like scope creep for a
  teaching guide; I kept the qualitative recommendation (single observer + `reactive.value`, not a `reactive_read`
  loop, for graphs where box-select floods matter) without republishing numbers I didn't re-measure.
- **Dropped the old report's CSS override snippet** for cosmetic upstream defaults (white background in dark mode,
  hover border, resize handle). It's a real, verified-still-present cosmetic quirk, but it felt like a "nice to
  have" footnote rather than something worth a dedicated subsection; happy to add it back as a one-liner in
  "Gotchas" if the maintainer wants it restored.
- **The showcase gallery app keeps the old report's `node:selected` CSS style rule** (black border on selected
  nodes) even though clicking a node now also drives `clicked_node()`-based focus styling. Both mechanisms are
  real and independently useful (one is "this node is selected," the other is "this node was last clicked and its
  neighborhood is focused"), and they compose fine visually, but it's worth a maintainer's eyes on whether showing
  both in one showcase app is too much at once.

## Editor's notes for the website

- **Strongest sections**: "Coordinating multiple views" (all three patterns got clean, convincing before/after
  pairs) and the showcase gallery app screenshots (`gallery_showcase_click.webp` especially -- colorful communities
  plus a clear focus effect reads well at a glance). I used `gallery_showcase_click.webp` as the hero.
- **Could trim for a shorter page**: the "What you can build" section's pandas-edgelist example is the weakest of
  the four highlights (a tiny 8-node synthetic dependency graph isn't as visually interesting as the Les Mis
  examples around it); it earns its place for teaching "build from a data frame," but if the page needs to
  shrink, this is the first candidate to cut or fold into prose.
- **The accessor reference table is short** (two rows) because this renderer only has two accessors, both the same
  shape (click -> element JSON). That's accurate, not a gap -- don't pad it.
- **Rate limiting section is short for the same reason**: nothing on this renderer is rate-limited by default.
  I chose to explain *why* precisely (the per-node-widget vs. top-level-widget distinction) rather than write a
  one-line "not applicable," since it's a genuine, verified, non-obvious finding that would otherwise look like an
  oversight.

## Cross-widget pairings

None in this pass. Every "coordinating multiple views" pattern pairs the graph with plain Shiny UI (detail cards,
selectize inputs, a slider), not a second shinywidgets output, since the most natural ipycytoscape pairings
(click -> table of neighbors, selection -> table) are adequately served by `ui.TagList`/`ui.tags.ul` text and
didn't need a real table widget to make the point. If the coordinator wants a cytoscape-plus-table or
cytoscape-plus-plot cross-link for the linked-views article, the `clicked_node()` neighbor list in
`examples/06_clicked_node.py` is the easiest seam to extend (swap the `ui.TagList` for `@render.data_frame`).

## What I dropped from the old report and why

- Full PR-review material (merge conflicts, nits about the PR diff, file-by-file line references): not relevant
  post-merge; this guide targets users, not reviewers.
- The detailed performance-scaling table (200/1000/3000/6000-node render times): kept the qualitative conclusion
  ("comfortable into the low thousands, slow beyond; use ipysigma for bigger graphs") in "Gotchas and
  limitations," dropped the specific numbers since I didn't re-measure them and didn't want to restate
  unverified-this-pass figures as current fact.
- The upstream-issue-filing checklist (a, b, c, ... items aimed at ipycytoscape maintainers): out of scope for a
  user-facing guide.
- The "open questions for the maintainer" about accepting Cytoscape JSON dicts directly and shipping CSS overrides
  by default: these are shinywidgets roadmap questions, not guide content; leaving them for the coordinator if
  useful context from the old report should carry forward.

## Update 2026-11-11 (main @ 32ca7035)

Versions: ipycytoscape 1.3.3, networkx 3.7, shiny 1.9.0, shinywidgets 0.8.2.post1.dev135+g32ca7035 (editable
install from the worktree at `32ca7035`). Worktree:
`/private/tmp/claude-502/-Users-cpsievert-github-py-shinywidgets/ce388f54-2d12-4580-8021-8300841b1d00/scratchpad/main-wt`.
Ports used: 8301-8305 (assigned range 8300-8399).

### What changed in the guide, and why

- **#441 renames were already applied** before this pass started (`clicked_node()`/`clicked_edge()` method names,
  front matter, prose, gallery apps) -- confirmed by grep, no `node_clicked`/`edge_clicked` method calls remained
  anywhere in `guide.md`, `examples/`, or `gallery/`. Only stale screenshot *filenames*
  (`node_clicked_before.webp`, `edge_clicked_before.webp`, etc.) still used the old name; left as-is since renaming
  image files isn't user-visible and the brief's #441 instruction is about accessor names, not asset paths.
- **Added `selected_nodes()`/`selected_edges()` (#428) as the lead selection pattern.** The accessor reference
  table now has four rows instead of two. The old "Beyond the accessors: reactive_read" section's full
  per-child `reactive_read(node, "selected")` loop recipe was replaced by the new accessors; `reactive_read` is
  now only taught for `grabbed` (not covered by any accessor) and as a "going past the accessors at very large
  scale" footnote.
- **Rewrote the "kept vs. re-seeded" story per #437.** The old guide said `clicked_node()`/`clicked_edge()`
  "reset to `None` on every re-render" -- this was true pre-#437 and is now false; they **keep** their value
  across a re-render until the user clicks the new graph. Verified directly: ran
  `tests/playwright/ipycytoscape_accessors` (3 passed, including
  `test_clicks_still_fire_after_rerender`) and `tests/unit/test_cytoscape_accessors.py::test_click_accessors_are_retained`.
  `selected_nodes()`/`selected_edges()` **re-seed** from the new graph's children on every render (confirmed via
  `tests/unit/test_cytoscape_accessors.py::test_renderer_selected_round_trips_and_keeps_state`, which shows the
  seed re-emits from the live `selected` state at each `on_render()`, and the PR #437 description, which lists
  "cytoscape selections" explicitly as a re-seeded example alongside bokeh/jscatter/bqplot).
- **Shrunk "Rate limiting".** `rate_policy`/`rate_delay` now reach the graph's child `Node`/`Edge` widgets (#404)
  and override `selected_nodes()`/`selected_edges()`'s own 0.25s debounce default -- confirmed by running
  `tests/unit/test_ipycytoscape.py::test_rate_policy_registers_on_child_nodes_and_edges` (passes on current
  main). The old section's claim ("the kwargs are close to a no-op for this renderer") is gone.
- **Added "Reading an accessor on demand"** (new example `13_read_on_demand.py`): a download-button handler reads
  `selected_nodes()` with nothing ever displaying it reactively first, demonstrating the no-warm-up headline
  capability from #437.
- **Fixed a real crash in `gallery/template_network_explorer.py`.** Its `detail()` output did
  `next(n for n in g.nodes if str(n) == clicked["data"]["id"])` with no default. Pre-#437, `clicked_node()` reset
  to `None` on every re-render, so a graph switch always saw `clicked=None` and never reached this line. Post-#437,
  `clicked_node()` is **kept** across re-render, so after clicking a karate-club node and then switching to Les
  Misérables, the retained id (e.g. `"33"`) doesn't exist in the new graph and `next()` raises `StopIteration`,
  which Shiny surfaces as `RuntimeError: coroutine raised StopIteration` and kills that output. Reproduced on
  current main, then fixed with a `next(..., None)` default and a graceful fallback. This is a **shinywidgets
  behavior change surfacing a latent bug in our own gallery app**, not an upstream or shinywidgets defect --
  flagging it because any other guide/gallery app with a similar "look up the clicked id in a graph that might
  have changed" pattern should be checked for the same thing.
- Updated front matter `accessors:` to `[clicked_node, clicked_edge, selected_nodes, selected_edges]`.

### New/edited examples -- verification status

| file | ran | gesture | accessor confirmed | screenshot(s) looked at |
|---|---|---|---|---|
| `examples/08_selected_nodes.py` (replaces `08_selection_reactive_read.py`) | yes | shift-drag box select (canvas pixel drag, cose layout) | `selected_nodes()`: 29 characters, 67 ties, density 0.17 -- matches the visually highlighted (red) cluster | `selection_before.webp`, `selection_after.webp` (replaced, now show the accessor-based app) |
| `examples/13_read_on_demand.py` (new) | yes | shift-drag box select, then click "Download selected characters" | `selected_nodes()` read inside a `@render.download_button` handler that was never displayed reactively; downloaded CSV's 30 rows matched the visually selected set exactly | `read_on_demand_before.webp` (new), `read_on_demand_download.webp` (new, screenshots the downloaded file's content via a `file://` navigation) |
| `gallery/showcase_les_miserables.py` (edited) | yes (existing pattern re-verified via the same accessor, not re-screenshotted -- see note below) | n/a (code change only: `reactive_read(n, "selected")` loop -> `network.selected_nodes()`) | Same accessor/mechanism as `08_selected_nodes.py`; not separately re-screenshotted since the visual output is identical to the existing `gallery_showcase_select.webp` (same underlying `selected` trait, same restyle, just read through the accessor now instead of a hand-rolled loop) | existing `gallery_showcase_*.webp` not stale (no visual change) |
| `gallery/template_network_explorer.py` (edited: bug fix) | yes | click a karate-club node, then switch to Les Misérables via the Graph selectize | Confirmed via server log: raised `RuntimeError: coroutine raised StopIteration` before the fix, no traceback and a graceful "Click a node..." fallback after | not added to `guide.md` (internal bugfix, not a documented pattern); screenshotted during verification (`template_after_graph_switch.webp`, scratch only) |

Accessor coverage this pass: `clicked_node()` and `clicked_edge()` -- re-confirmed via the existing committed
Playwright suite (not re-driven manually, since nothing about their gesture/payload changed, only their
across-re-render semantics, which the suite already covers). `selected_nodes()`/`selected_edges()` -- verified
directly with a real shift-drag box-select gesture and a Python-side read, both in `08_selected_nodes.py` and in
`13_read_on_demand.py`.

### Items from the old "Bugs found" now fixed

None of the three items in the 2026-10-30 "Bugs and surprises found" list were about accessor semantics, so none
are obsoleted by this pass's changes:
1. The `height="auto"` regression was already fixed pre-#441 and remains fixed (not re-verified this pass, no
   code in that path changed).
2. The old "`rate_policy`/`rate_delay` are close to a no-op for this renderer" finding is now **obsolete** (not a
   bug anymore): #404 made `rate_policy`/`rate_delay` reach the child `Node`/`Edge` widgets. Superseded by this
   pass's rewritten "Rate limiting" section.
3. The three upstream ipycytoscape bugs (node removal corrupts the graph, `selected` write toggles
   selectability, invalid `widget.on()` event name corrupts the registry) are unrelated to the accessor redesign
   and not re-verified this pass; still listed in "Gotchas and limitations".

### New bugs found (2026-11-11)

1. **[shinywidgets-adjacent, our own gallery app] `gallery/template_network_explorer.py` crashed on current main**
   after switching graphs following a click, due to `clicked_node()`'s new kept-across-re-render semantics (#437)
   interacting with an unguarded `next(...)` lookup. See above. Fixed in this pass; not a shinywidgets library
   bug, but worth the maintainer's attention as a pattern other agents' gallery apps might share (anywhere a
   retained click/selection payload's id is looked up in data that can change shape across a re-render).

No shinywidgets library bugs or docstring errors found this pass; `shinywidgets/_cytoscape.py` and the
`render_ipycytoscape` docstrings in `_render_widget.py` were read closely and match observed behavior exactly
(kept/re-seeded semantics, rate-limit scope, selection setup requirements).

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views." This guide's own intro and "Gotchas" already state
the scale story exactly (one ipywidget per element, comfortable into the low thousands, see ipysigma beyond
that) and were already verified in an earlier pass, so the new section just restates it in the shared shape and
cross-links to `ipysigma/guide.md#large-data`. No new example or measurement needed. Links forward to the
not-yet-written `../articles/performance/article.md#three-approaches-to-large-data` (Task 7, same wave) --
expected `check_docs.py` anchor warning.
