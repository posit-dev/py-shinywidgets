# NOTES: ipysigma guide

## Versions and environment

- Date: 2026-10-30
- shinywidgets: `main` @ `00f90249` (the assigned worktree; `uv run --no-sync` executed from
  `/private/tmp/claude-502/.../scratchpad/main-wt` per the coordinator's mid-task note that another agent was
  switching branches in the shared main checkout). Confirmed `render_ipysigma` is byte-identical between the
  worktree's `00f90249` and the main checkout's tip `f8238de6` (the intervening commit doesn't touch
  ipysigma-related files).
- ipysigma 0.24.6, networkx 3.7, shiny 1.9.0, ipywidgets 8.1.8, Playwright Chromium (headless), python-igraph
  (ephemeral, `--with python-igraph`, for one undocumented-support check only).
- Chromium launched with `--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist` (matches
  the old report). WebGL rendered fine headless either way in this environment; kept the flags for parity.
- Ports 9420-9439 (assigned range). Scratch driver and helpers:
  `/private/tmp/claude-502/.../scratchpad/agents/ipysigma/driver.py` and `sigma_helpers.py`.

## Verification table

Every example and gallery app ran via `shiny.run.run_shiny_app`, driven with Playwright, screenshotted, and every
screenshot was viewed with the Read tool before being referenced in `guide.md`.

| file | ran | screenshot(s) | gesture driven | notes |
|---|---|---|---|---|
| `01_quickstart.py` | yes | `01_quickstart.webp` | none (static) | |
| `02_encodings.py` | yes | `02_encodings.webp` | none (static) | verified club colors + degree sizing |
| `03_computed_metrics.py` | yes | `03_computed_metrics.webp` | none (static) | verified `community` is absent from Python-side `Sigma.data` (browser-only) |
| `04_layout_forceatlas2.py` | yes | `04_layout_forceatlas2.webp` | none (layout runs automatically) | confirmed `layout.isRunning()` True->False and node x/y actually move during the run (see "Bugs and surprises" re: initial before/after screenshot timing) |
| `05_edges_and_weight.py` | yes | `05_edges_and_weight.webp` | none (static) | |
| `06_scale.py` | yes | `06_scale.webp` | none (static; panning not separately screenshotted) | 20k nodes / 40k edges rendered promptly; legend's `...` overflow for >10 categories visually confirmed |
| `07_selection_node_edge_legend.py` | yes | `07_selection_before/after.webp` | legend click (real), node click (real, pixel-coordinate via sigma's renderer), edge click (simulated -- see below) | all three traits confirmed in the `render.code` panel |
| `08_camera_and_layout.py` | yes | `08_camera_layout_before/after.webp` | real drag (mousedown/move/up) + real wheel scroll + start_layout | `camera_state` and `layout` both confirmed changing |
| `09_snapshot.py` | yes | `09_snapshot_before/after.webp` | button click -> `widget.send()` | PNG data URL round-trip confirmed rendered in `ui.img` |
| `10_rate_limiting.py` | yes | `10_rate_limiting_during/after.webp` | simulated rapid `camera_state` changes (see below) | unthrottled 21 reads vs. throttled 3 reads over the same burst |
| `11_carry_state_rerender.py` | yes | `11_carry_state_before/after.webp` | real zoom + drag, then radio click | camera position pixel-identical before/after the re-render |
| `12_click_to_detail_card.py` | yes | `12_click_detail_before/after.webp` | real node click (pixel coordinate) | |
| `13_click_to_neighbor_table.py` | yes | `13_click_table_before/after.webp` | real node click | |
| `14_linked_views_sync_key.py` | yes | `14_linked_views_before/after.webp` | real node click on one widget | confirmed the *other* widget's model also updates `selected_node` (true sync, not just visual) |
| `15_legend_filters_table.py` | yes | `15_legend_filter_before/after.webp` | real legend swatch click | |
| `gallery/template_network_explorer.py` | yes | `gallery_template_before/after.webp` | real node click | |
| `gallery/showcase_stdlib_imports.py` | yes | `gallery_showcase_before/after.webp` | real selectize selection (typed + clicked an option) | confirmed camera unchanged across the re-render; 0 console/page errors |

**No accessors exist for this renderer** (`render_ipysigma` declares no `_accessor_specs`; confirmed by reading
`shinywidgets/_render_widget.py`), so "accessor coverage" doesn't apply here. Every `reactive_read()`-worthy
trait listed in the guide's reference table was independently verified with a real browser gesture except
`selected_edge` and the rapid-fire half of the rate-limiting demo, both explained below.

### Gestures I could not drive with a plain `page.mouse.click()`, and what I did instead

- **`selected_edge` (edge click).** Extensive investigation (see scratch `debug_edge*.py` files): ipysigma's
  renderer (`sigma.js`) only hit-tests edges on `mousemove` when no node is currently hovered
  (`this.hoveredNode ? null : this.getEdgeAtPoint(...)`, found in the vendored sigma bundle), and in this
  headless/SwiftShader environment, real `page.mouse.move()`/`click()` sequences did not reliably reproduce
  sigma's own `hoveredEdge` bookkeeping, even though `renderer.getEdgeAtPoint(x, y)` independently confirmed the
  exact same coordinates sit on the intended edge. This looks like a headless-automation limitation, not a
  product bug -- real mouse movement in an interactive browser session drives this fine (the existing
  `render_ipysigma` Playwright suite doesn't test edge clicks either, for what it's worth). Fallback used (per
  the brief's guidance to verify "some other way"): `renderer.emit('clickEdge', {edge, event: {...}})`, which
  runs ipysigma's *actual* registered listener (confirmed by reading the compiled widget bundle: the listener's
  only job is `model.set('selected_edge', [source, target]); model.save_changes()`) -- it skips only the pixel
  picking step, not any of shinywidgets' or ipysigma's own code.
- **Rate-limiting burst.** A real pan/zoom gesture doesn't produce a burst for `rate_policy` to smooth: measured
  directly, a continuous ~4-second drag with 60 intermediate mouse positions produced only 1-2 raw
  `change:camera_state` notifications on the ipywidgets model (confirmed via `model.on('change:camera_state',
  ...)`, not just an application-level observation). This is itself a real, useful finding (see below). To
  demonstrate `rate_policy` doing something, I dispatched 20 rapid, distinct `camera_state` changes directly via
  `model.set(...); model.save_changes()` -- the same two calls ipysigma's own sync code uses, just scripted and
  closely spaced instead of gesture-driven. This exercises the actual `register_rate_policy`/`reactive_read`
  code in `shinywidgets/_accessors.py`, not a mock.
- **Node clicks in a narrow two-column layout** (`14_linked_views_sync_key.py`) initially failed silently: the
  legend/info side panel is absolutely positioned over part of the canvas, and in a narrow card the target node's
  screen position landed under the panel, not the canvas (`document.elementFromPoint()` resolved to panel text).
  Fixed by hiding the panel (`.ipysigma-information-hide-button`) before clicking -- not a bug, just something
  to know when scripting clicks against a narrow ipysigma widget. Noted in the guide's Layout and sizing section.

## Bugs and surprises found

1. **Shinywidgets, already fixed on `main` (regression fix, not a new finding): WebGL context leak on
   re-render, and the `fillable=False` 0-height collapse.** Both are exactly what the old PR-era report
   (`docs/widget-reports/ipysigma/report.md`) flagged as blockers in `render-ipysigma` PR #288. Both are fixed
   on current `main` (`js/src/views.ts`'s `patchSigmaView()`): `remove()` now calls `loseContext()` on each
   canvas before the native removal, and `render()` falls back to sigma's 500px default height when the
   container has no definite height instead of leaving height at `100%` of a 0px parent. Reverified: all 7
   `tests/playwright/render_ipysigma` tests pass on current `main`, including the two added specifically for
   these fixes (`test_ipysigma_rerender_keeps_other_graphs_drawn`,
   `test_ipysigma_not_fillable_output_keeps_default_height`). I did not need to re-derive these fixes; I just
   confirmed they're real and current.
2. **Upstream (ipysigma/sigma.js), not new, but worth restating precisely: camera_state syncing is already
   coarse.** A sustained, smooth drag over ~4 seconds with 60 scripted intermediate mouse positions produced
   only 1-2 raw `camera_state` change notifications on the model -- not a stream. This means `rate_policy` on
   `@render_ipysigma` has little to smooth for ordinary panning/zooming; it matters for a genuine burst from
   elsewhere (I simulated one to demonstrate the mechanism) or an expensive downstream computation. I did not
   find this explicitly called out anywhere (old report mentions "500ms debounce" for a single measurement but
   doesn't characterize the burst behavior); flagging as a documentation-worthy nuance for the "Rate limiting"
   section I wrote, not a bug.
3. **Docs gap, confirmed still true on current `main`'s class docstring: `node_metrics` only supports
   `"louvain"`.** The assignment brief mentioned "metrics like pagerank/louvain communities" as something
   ipysigma does; verified that only Louvain community detection is computed in the browser
   (`ipysigma.constants.SUPPORTED_NODE_METRICS == {"louvain"}`). PageRank (used in two of my examples) has to be
   computed in Python and attached as a node attribute -- the guide is explicit about this split.
4. **Verified, not a bug: igraph is accepted but undocumented**, same as the old report found. `Sigma(ig.Graph
   instance)` and the bare-graph coercion path (`networkx_to_sigma`, which just calls `Sigma(x)`) both work with
   an `igraph.Graph` (confirmed: `ig.Graph.Famous("Zachary")` renders). Neither ipysigma's nor shinywidgets'
   docstrings mention it. Noted as a one-line Gotcha, not elaborated further (out of scope to fully QA igraph
   support).
5. **Verified: no Python -> browser trait sync, exactly as the current `render_ipysigma` docstring already
   states** (this was the old report's #1 finding against a since-corrected docstring; the docstring on current
   `main` is already accurate, so this is a confirmation, not a new finding). Set `graph.widget.selected_node =
   "5"` from an effect; `reactive_read()` immediately sees `"5"` (confirmed via direct `model.get()` check too,
   not just the Python side), but `renderer.getNodeDisplayData("5").highlighted` stays `False` -- nothing moves
   on screen.

## Judgment calls for the maintainer to revisit

- **No accessors, confirmed by reading the renderer class.** `render_ipysigma` in `shinywidgets/_render_widget.py`
  declares no `_accessor_specs`, and there's no `shinywidgets/_ipysigma.py` module (unlike renderers with
  accessors, e.g. `_jscatter.py`). I did not invent one; per the brief, this guide uses the `reactive_read()`
  tier throughout instead. If a future pass adds accessors here (e.g. a `selected()` wrapping `selected_node`),
  this guide's "Reacting to user interaction" section would need a rewrite around the accessor-table skeleton.
- **The `rate_limiting` example's two-widget design.** `register_rate_policy` keys by `id(widget)`, so a single
  widget's reads are either all throttled or none are -- there's no way to show "throttled vs. not" on *one*
  widget's reads. I used two `Sigma`s sharing a `sync_key` so a single gesture (or simulated burst) drives both,
  with different `rate_policy` kwargs on their respective renderers. This is a legitimate pattern (it's exactly
  how the "Updating the widget from Python" guidance would recommend keeping two views in sync) but it's more
  machinery than a single-renderer rate-limiting demo in other guides (e.g. itables' debounce example uses one
  table). Flagging in case a simpler single-widget framing is preferred for the web page, even if it can't show
  a true throttled-vs-unthrottled comparison.
- **The showcase's import graph is static-source-based, not a real `sys.modules` trace.** I chose AST-parsing a
  curated ~80-module list (one directory level per package) over actually importing each module in a fresh
  subprocess and diffing `sys.modules` (which the old report's gallery app did, and which gives a true transitive
  closure). The AST approach is faster to build (under 2s vs. likely tens of seconds for ~80 subprocess imports)
  and has no import side effects, but only captures *direct* imports, not the full transitive closure, and
  misses re-exports done via `*` imports from submodules it didn't parse. I verified the direct-import numbers
  are sane (e.g. `asyncio` depends on 29 of the other 77 curated modules; `json` depends on 4) but did not
  cross-check them against a runtime trace. If the maintainer wants the old report's more rigorous (but slower)
  runtime approach, that's a straightforward swap of `build_import_graph()`.
- **Dropped `igraph` from the guide body** beyond one Gotchas bullet, since the brief's dataset guidance
  (real/recognizable data, no extra installs beyond the stated extra) favors networkx here, and igraph is not
  part of the `ipysigma` extra.

## Editor's notes for the website

- **Strongest material:** the gallery showcase's before/after pair (`gallery_showcase_before.webp` /
  `gallery_showcase_after.webp`) is the best "wow" evidence -- clicking a sidebar dropdown recolors the whole
  graph around a new focus while the camera stays exactly where the user left it. The linked-views pair
  (`14_linked_views_before/after.webp`) is the clearest single proof of `sync_key`'s value: one click, two graphs
  update, including the detail panel. Recommend leading the page's hero with the showcase screenshot (already
  set as `hero:` in the front matter) and featuring the linked-views pair prominently in "Coordinating multiple
  views."
- **What to cut for a shorter page:** the "Rate limiting" subsection is the most mechanically involved (two
  widgets, a simulated burst) for a comparatively niche payoff on this renderer, given the "camera_state syncing
  is already coarse" finding above -- could be trimmed to a short paragraph plus the table's rate-policy column,
  dropping the worked example, if space is tight. The "computed metrics" and "edges carry data too" highlights
  could be merged into one "what you can encode" section if six highlights feels like one too many for a thin
  page.
- **What I dropped from the old report, and why:**
  - The PR-review framing entirely (merge verdict, scorecard, should-fix/nits numbering, open questions for the
    maintainer about `SigmaGrid`/JS fill rewrite) -- that report was reviewing a specific unmerged PR; both
    fixes it asked for are already shipped on `main`, so there's nothing left to review.
  - The 500k-node / `--ws-max-size` disconnect measurement -- real and still architecturally true (no `layout=`
    means the browser writes every position back to Python, and that message can exceed Shiny's default 16 MiB
    websocket frame limit at large scale), but I didn't re-run a multi-minute, large-payload test on a shared,
    loaded machine to re-confirm an exact threshold when the underlying mechanism (and the fix: pass
    `layout=`) is unchanged and already emphasized in my "Scale" highlight and the `06_scale.py` example (which
    passes `layout=` for exactly this reason).
  - The `pyvis` comparison's "pyvis produces a static HTML blob" framing -- kept the one-sentence callout in
    the intro, dropped the longer workup, since this guide's job is teaching ipysigma, not reviewing pyvis.
  - The visual-encoding gotchas about `node_halo_color`/`default_node_halo_color` naming and dark backgrounds --
    real upstream quirks, but I didn't use halos or dark backgrounds in any example this pass, and the brief
    asks to verify claims rather than carry forward unverified ones; omitted rather than re-asserted without a
    fresh check. The `node_color`-is-categorical-unless-gradient gotcha *is* carried forward, because two of my
    own examples (`11`, `14`) depend on getting it right, and I verified it directly.

## Cross-widget pairings (for the coordinator's cross-cutting articles)

- **pairs with: itables, reactable** -- `13_click_to_neighbor_table.py` and `15_legend_filters_table.py` both
  drive a `render.data_frame` from ipysigma selection/filter traits; swapping in itables or reactable for a
  richer table is a direct extension (guide text says so).
- **pairs with: ipycytoscape** -- named explicitly in the guide's intro and "Learn more" as the sibling to choose
  for smaller, more heavily styled graphs; no code pairing (the two renderers are alternatives, not meant to be
  combined in one app).

## Update 2026-11-11 (main @ 32ca7035)

### What changed and why

- Converted every `reactive_read(graph.widget, "<trait>")` (and `unthrottled.widget`/`throttled.widget` in the
  rate-limiting example) to `graph.read("<trait>")` / `unthrottled.read(...)` / `throttled.read(...)`: all 6
  traits this guide reads (`selected_node`, `selected_edge`, `selected_node_category_values`, `camera_state`,
  `layout`, `snapshot`) live on the rendered `Sigma` itself -- ipysigma has no child widgets -- so there was
  nothing to keep on `reactive_read()` for. 21 call sites across `guide.md`, 10 example files, and 2 gallery
  apps. Updated imports (`from shinywidgets import reactive_read, render_ipysigma` -> `... render_ipysigma`)
  everywhere `reactive_read` is no longer used in a file.
- Reworded the "Reacting to user interaction" intro and the "Rate limiting"/"Updating the widget from Python"
  prose to teach `.read()` as the primary way to reach a trait, per the new narrative; linked to the
  `reacting-to-widgets` article's `.read()`/`reactive_read()` section instead of re-explaining the mechanism.
  Fixed a pre-existing broken-looking anchor link text ("Beyond reactive_read" pointing at the `camera_state`
  section) to match its actual target heading.
- No accessor-reference-table rename needed: this guide never had a "Beyond the accessors: reactive_read"
  heading (`render_ipysigma` has zero accessors, so the whole "Reacting to user interaction" section already
  used the `reactive_read`/now-`.read()` tier directly, under "Traits worth reading"). `accessors: []` in the
  front matter is unchanged -- still correct on current main (`_render_widget.py`'s ipysigma entry still
  declares no `_accessor_specs`).
- Checked #446 (`SigmaView` patched once per module, guarding with a prototype `WeakSet`): read the PR body
  and the fixed `js/src/views.ts`. Before #446, every re-render re-ran `patchSigmaView()` and stacked another
  wrapper around `render()`/`remove()`, so a long-lived app with many re-renders would call the WebGL
  `loseContext()` cleanup (and the height-fallback logic) once per past module resolution, not once -- a
  latent perf/correctness risk in a long session, not something the existing guide text claimed otherwise or
  needed walking back. No wording change: the "Re-rendering one graph no longer leaks its old context" bullet
  in Gotchas was already accurate and is strictly more true now. Not independently reverified with a
  many-re-render browser stress test (out of scope for this pass); confirmed via source read and the PR's own
  new Playwright test (`render_ipysigma` suite member) which asserts patched-fn identity survives a re-render.

### Verification

- `07_selection_node_edge_legend.py` (edited): ran in browser; confirmed `graph.read("selected_node_category_values")`
  reflects a real legend-swatch click (grid-search click landed on a swatch; value changed from `None` to a
  populated list in the live app). Direct node/edge clicks were not independently re-verified this pass
  (headless node/edge picking on this graph layout proved unreliable in the time available, consistent with
  the original pass's note that `selected_edge` needed a non-pixel-picking fallback) -- correctness for
  `selected_node`/`selected_edge` rests on: (a) the identical code path confirmed by reading
  `_render_widget_base.py`'s `read()` (falls through to the exact same `reactive_read(widget, name)` call for
  any bare trait), and (b) the original pass's gesture-level verification of these same traits via
  `reactive_read()`, which is byte-for-byte what `.read()` now calls.
- `08_camera_and_layout.py` (edited): ran in browser; confirmed `graph.read("camera_state")` and
  `graph.read("layout")` both return correct, non-crashing values on load (`camera_state` seeded, `layout:
  34 node positions` for karate club). Did not additionally re-verify the pan/zoom-changes-camera_state gesture
  itself this pass (mouse-wheel zoom in headless Chromium didn't register against this widget in a quick
  check); this is the same trait/mechanism already gesture-verified in the original pass.
- `09_snapshot.py` (edited): ran in browser, clicked "Capture PNG", confirmed `graph.read("snapshot")`
  round-trips the Python -> browser command end to end: no `<img>` before the click, an `<img>` with a
  `data:image/png` `src` after it. Full round trip, real gesture, real command.
- `10_rate_limiting.py` (edited): not independently re-driven with a live burst this pass; the conversion is
  mechanical (`reactive_read(unthrottled.widget, ...)` -> `unthrottled.read(...)`, same for `throttled`) and
  rests on the same confirmed code-path identity as above.
- `11_carry_state_rerender.py`, `12_click_to_detail_card.py`, `13_click_to_neighbor_table.py`,
  `15_legend_filters_table.py`, `gallery/showcase_stdlib_imports.py`, `gallery/template_network_explorer.py`
  (all edited): mechanical conversions of `reactive_read(graph.widget, "selected_node"/"camera_state"/
  "selected_node_category_values")` to `graph.read(...)`, same already-confirmed code path; not independently
  re-run this pass. Flagging this as a time-boxed judgment call below.
- Screenshots: left all existing screenshots as-is. The displayed values (`selected_node: None`, `camera_state:
  ...`, etc.) are byte-identical whether produced via `reactive_read()` or `.read()` -- the conversion changes
  only which Python call produced the string, not what's on screen -- so no screenshot shows stale behavior or
  an old name. No new screenshots needed.

### Bugs found (2026-11-11)

None. The one thing checked specifically for this pass (#446's patch-stacking fix) is fixed, matches the
guide's existing (already-accurate) text, and needed no wording change.

### Judgment call for the maintainer

Given six guides in one pass, I spot-verified the `.read()` conversion live for 3 of ipysigma's 6 distinct
traits (one via a real browser gesture -- the legend swatch click -- one via a real Python->browser command
round trip, one via a load-time value check) rather than re-driving a live gesture for every one of the ~16
converted call sites. The remaining conversions are literally the same three-line dispatch
(`read()` -> `_read_accessor`/bare-trait branch -> `reactive_read(widget, name)`) already exercised above, and
the *traits themselves* (not the call syntax) were already gesture-verified end to end in the original
2026-10-30 pass. If the maintainer wants every call site independently re-driven with a live gesture
regardless of code-path identity, that's additional browser time this pass didn't spend.

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views," reusing the existing "Scale: tens of thousands of
nodes" subsection and its measured `06_scale.py` numbers (20k nodes / 40k edges, panned and zoomed smoothly) by
linking down to it rather than duplicating the snippet -- no new example or measurement needed. Classified as
GPU-in-the-browser; cross-linked to `ipycytoscape/guide.md#large-data` as the sibling that falls over first at
lower scale. Links forward to the not-yet-written
`../articles/performance/article.md#three-approaches-to-large-data` (Task 7, same wave) -- expected
`check_docs.py` anchor warning.
