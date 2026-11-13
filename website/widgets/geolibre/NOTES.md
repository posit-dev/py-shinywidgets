# NOTES: geolibre guide

Versions: geolibre 3.5.2, shiny 1.9.0, matplotlib 3.11.2, pandas (from the shared venv), requests 2.34.2.
shinywidgets commit: `00f90249` (main, 2026-10-30). Date: 2026-10-30.

PR #360 ("use geolibre's async command methods when available") is open but not on main; everything here reflects
current `main` only. See "If #360 lands" at the end of this file.

## Verification table

All apps run via `uv run --no-sync shiny run` from the worktree, driven with Playwright (Chromium headless,
default GPU settings -- no `--use-angle=swiftshader` flags were needed; the embedded app's own canvas rendered
fine headless), screenshots read back with the Read tool before referencing them.

| File | Ran | Screenshot | Gesture driven | Notes |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes | n/a (static) | |
| examples/02_vector_and_point_layers.py | yes | yes | n/a (static) | |
| examples/03_styling_and_popups.py | yes | yes (before/after) | click (popup), slider+select (verified restyle live, screenshot not required for that part) | |
| examples/04_snapshot_export.py | yes | yes | real download clicked; verified bytes are a valid PNG (1062x1152) | |
| examples/05_toolset_and_legend.py | yes | yes | n/a (static; Measure panel opens via `show_control`) | |
| examples/06_events_and_detail_card.py | yes | yes (before/after) | click (with Identify armed) | |
| examples/07_reading_project_state.py | yes | yes (before/after) | drag-pan | confirmed `bbox` appears only after first browser sync |
| examples/08_driving_from_inputs.py | yes | yes (before/after) | select_option | |
| examples/09_fly_to_worker_thread.py | yes | yes (before/after) | select_option + click; found+fixed a real bug, see below | |
| examples/10_viewport_to_chart.py | yes | yes (before/after) | scroll-zoom | found+fixed the same `bbox`-missing race |
| examples/11_table_to_map.py | yes | yes (before/after) | click a table row | |
| examples/12_layout_sizing.py | yes | yes | n/a (visual + measured heights) | measured 508px / 300px / 250px for fill/fixed/sized |
| gallery/template_city_explorer.py | yes | yes (before/after) | click a marker | |
| gallery/showcase_density_dashboard.py | yes | yes (before/after) | click a table row; real PNG download | |

Accessor coverage: **none** -- `render_geolibre` declares no `_accessor_specs` (confirmed by reading
`shinywidgets/_render_widget.py`; its `Parameters` section lists only `width`/`height`/`fill`/`fillable`, unlike
sibling renderers with accessors which also list `rate_policy`/`rate_delay`). The guide documents the
event-callback and `reactive_read` tiers instead, both verified with real gestures above.

## Bugs found

**In shinywidgets' own shipped example (`examples/geolibre/app.py` on main) -- a real, reproducible bug:**

- The "Fly there (animated)" button's `fly_to_city` `@extended_task` reads `input.city()` **inside its own async
  body**:
  ```python
  @extended_task
  async def fly_to_city():
      lng, lat = CITIES[input.city()]   # <-- raises
      ...
  ```
  `extended_task` functions cannot read reactive sources from inside their body (confirmed from Shiny's own
  docstring: "they cannot access reactive sources... the decorated function must take them as parameters"). I
  reproduced this directly: running `examples/geolibre/app.py` from the worktree, selecting a city, and clicking
  "Fly there" invokes a task that immediately errors with `RuntimeError: You're not allowed to read reactive
  sources from inside a Extended Task. Instead, read the reactive sources before calling the extended task, and
  pass them in as function arguments.` The button is otherwise wired correctly (the worker-thread pattern itself
  works, as every `09_fly_to_worker_thread.py` run here confirms) -- it's specifically this one call site. Minimal
  repro: `docs/widget-guides/geolibre/examples/09_fly_to_worker_thread.py` is the fixed version (reads
  `CITIES[input.city()]` in the `@reactive.effect` and passes it to `.invoke(*...)`); reverting to reading
  `input.city()` inside `fly_to_city`'s body reproduces the crash in under 5 seconds of driving. Not a shinywidgets
  *rendering* bug -- it's in the example app's Python, but it ships as the canonical "how to use blocking methods"
  reference and currently cannot work as written. Worth a one-line fix on main.

**Real race condition, affects any `reactive_read(widget, "project")["mapView"]["bbox"]` consumer:**

- `project["mapView"]` has `center`/`zoom`/`bearing`/`pitch` from the moment `Map(...)` is constructed in Python,
  but **not** `bbox` -- that key is filled in only once the browser's first state sync lands, a moment after the
  embedded app boots. A `@render.plot`/`@render.code` that indexes `["bbox"]` directly can hit a `KeyError` on
  the very first render, before self-healing on the next invalidation (once the real sync arrives). I hit this
  live in both `10_viewport_to_chart.py` and the showcase app (traceback with `KeyError: 'bbox'` at the exact
  `reactive_read(...)["mapView"]["bbox"]` line) but *not* in `07_reading_project_state.py` using the same
  pattern -- it's a genuine timing race (how long the output takes to first execute relative to the iframe boot),
  not deterministic per-file. Fixed in all three places with `.get("bbox")` + `req()`/a `None` check, and called
  out explicitly in the guide's Gotchas. This is a docs-worthy upstream-shaped quirk (geolibre's own design, not
  a shinywidgets bug), but it's exactly the kind of thing a user would silently hit and not understand.

**Upstream geolibre, long-standing, not a regression:**

- `Map.layout` shadows `ipywidgets.DOMWidget.layout` (geolibre's own `"embed"`/`"full"`/`"maponly"` string vs.
  ipywidgets' `Layout` object), producing one harmless "Cannot read properties of undefined (reading 'then')"
  console error per render. Matches the old report's finding exactly; still true on geolibre 3.5.2. Cosmetic,
  tolerated by the existing Playwright suite (`tests/playwright/render_geolibre/test_render_geolibre.py`), and
  documented here rather than treated as newly discovered.
- `fly_to()` acknowledges at animation *start*; a `get_center()` issued right after can read a mid-flight
  position. Matches `pr-341-flyto-open-issue.md`'s resolution notes exactly. Worked around in
  `09_fly_to_worker_thread.py` with an explicit `duration` and a 1s sleep before querying -- this is upstream
  behavior, not something shinywidgets can paper over.

**Confirmed fixed since the old report (`docs/widget-reports/geolibre/report.md`) -- noted so nobody re-chases them:**

- Local-file layers (`add_cog()`/`add_raster()` of a server-disk file) are **no longer same-host-only**. The old
  report's top "remaining limitation" is resolved: shinywidgets now mounts a loopback proxy at `/proxy/{port}/`
  (verified by reading `shinywidgets/_dependencies.py`'s `geolibre_app_mount()`/`_LoopbackProxyApp`, and by the
  passing `tests/playwright/render_geolibre/test_render_geolibre.py::test_geolibre_local_cog_via_proxy`). I didn't
  re-verify this myself end-to-end with a fresh repro (the existing Playwright test already covers it thoroughly,
  including a hand-crafted GeoTIFF and range-request checks), but I did confirm by reading the proxy-mount code
  and the docstring that the claim is accurate, and updated the guide's Gotchas to say so explicitly instead of
  repeating the old "local-host only" framing.
- The old report's "blocking RPC methods don't work in Shiny at all" finding is now "work from a worker thread,
  not the event-loop thread" -- geolibre >= 3.5.2's sleep-poll fallback (`opengeos/GeoLibre#3266`, referenced in
  `docs/plans/2026-10-26-geolibre-blocking-methods-followups.md`) closed this. Verified directly: `fly_to()` +
  `get_center()` round-trip via `extended_task`/`run_in_executor` in `09_fly_to_worker_thread.py`, and `to_image()`
  the same way in `04_snapshot_export.py` and the showcase (both produced valid, non-trivial PNGs: ~573KB and
  ~1.5MB respectively, confirmed with `file` after a real Playwright-driven download).

## Judgment calls

- No accessors exist on `render_geolibre`, confirmed by reading `_render_widget.py` directly (no `_accessor_specs`
  override, and the `Parameters` docstring section omits `rate_policy`/`rate_delay`, which only appear on
  renderers that declare accessors). I did not spend time trying to find an undocumented one.
- Used a single running dataset across almost the whole guide -- the US-states GeoJSON (with its `density`
  field) and a small hardcoded list of major US cities -- rather than a new dataset per section, matching the
  itables guide's stated approach of "one real dataset threaded through the page" for visual/narrative
  consistency. The showcase computes its "10 densest states" table and approximate state centroids directly from
  the same GeoJSON at runtime (polygon-vertex-average centroids, not true geometric centroids -- close enough for
  "fly to this state" and called out as approximate in the gallery file's header comment).
- `template_city_explorer.py`'s click handler matches the clicked marker to the nearest known city by squared
  distance rather than exact float equality. I tried exact equality first and it failed in testing -- not because
  GeoLibre rounds coordinates, but because it's simply a more robust pattern to teach (a reader's own data won't
  always round-trip bit-for-bit through a feature's GeoJSON serialization). Mentioned implicitly via the working
  code; didn't call it out as its own gotcha since it's a general GIS-click pattern, not geolibre-specific.
- Did not add a dedicated "drawing tools" example beyond the `show_control("measure", ...)` highlight. GeoLibre
  ships a full draw toolbar (polygons, lines, points) but driving it via Playwright (multi-click polygon drawing
  inside an iframe-in-iframe-like canvas) was judged lower value than the patterns already covered, given the
  brief's "fewer is fine, never pad" guidance. Mentioned only in the intro paragraph's "drawing and measuring"
  phrase.
- `set_identify()`'s payload enrichment (a plain click's event dict gains a `"features"` list once Identify is
  armed on a layer) is not spelled out anywhere in the `on_click()` docstring -- I discovered it empirically by
  probing in the browser (see `06_events_and_detail_card.py`'s approach). It's a legitimate, useful behavior
  (not a bug), just undocumented at the method level; worth flagging to the maintainer as a docstring gap in
  `geolibre` itself (upstream), not shinywidgets.

## If PR #360 lands

PR #360 ("use geolibre's async command methods when available") is still open. The investigation docs in this
repo (`pr-341-async-api-proposal.md`) describe the shape: geolibre would gain `async def request_async()` plus
per-method `*_async()` wrappers (`fly_to_async()`, `get_center_async()`, `to_image_async()`, ...), and
shinywidgets' PR would presumably make `render_geolibre`-adjacent code (or the methods themselves) prefer the
async path when the installed geolibre version supports it.

What would change in this guide if it lands:

- "Updating the widget from Python" would gain a second, simpler pattern for Shiny **async** contexts: directly
  `await map.widget.fly_to_async(...)` inside a plain `async def` effect or render function, no
  `reactive.extended_task`/`run_in_executor`/worker thread needed. The existing worker-thread pattern would likely
  stay documented as the one that works on *every* geolibre version and from *sync* contexts, with the async
  variant presented as the preferred option "if your installed geolibre supports it."
- `04_snapshot_export.py`'s `to_image()` download handler is already `async def` with a `yield`, so it would
  become a one-line change (`await map.widget.to_image_async()` instead of `run_in_executor`) -- worth noting as
  the cleanest example to update first, since it needs no thread-safety reasoning at all once async.
- The "can never work on Shiny's event-loop thread" framing in Gotchas would need to be qualified to "the *sync*
  command methods can never..." -- async variants are specifically designed to work there.
- I'd keep both patterns in the guide rather than replacing one with the other: PR #360 plus a geolibre release
  containing it would take time to reach most users' pinned versions, so the worker-thread pattern remains the
  one that works everywhere in the meantime.
- No change needed to the "project mutation" (non-blocking) methods, the event callbacks, `reactive_read`, or
  the layout/sizing sections -- none of that is affected by #360's scope.

## Pairs with

- **plotly / matplotlib** (generically) -- `10_viewport_to_chart.py` and the showcase's "states currently on
  screen" chart use a plain `@render.plot` (matplotlib) deliberately, to keep the second widget simple per the
  brief; either could be swapped for `render_plotly` for a nicer interactive chart.
- Any table renderer (**itables**, **reactable**, **ipydatagrid**) would substitute cleanly for the plain
  `render.data_frame` used in `11_table_to_map.py` and the showcase.
- **maplibre**, **leafmap**, **lonboard** -- all three are referenced in the guide's intro and "Learn more" for
  the "choose this vs. siblings" comparison; no shared code, just prose links.

## Editor's notes for the website

- Strongest sections: "Updating the widget from Python" (the project-mutation vs. blocking-command-method split is
  the single most important thing to get right with this widget, and the found-and-fixed `extended_task` bug
  makes the warning concrete rather than hypothetical) and the showcase gallery screenshot (map + table + chart +
  export, with the before/after row click making the link obvious at a glance).
- The "What you can build" section's styling/popup screenshot (`03_styling_and_popups_after.webp`) is the best
  single illustration of "this is a real GIS app, not a map widget" -- the popup, the layer panel, and the opacity
  slider are all visible in one frame. Good hero candidate if a more map-focused (less dashboard-y) hero is
  wanted instead of the showcase image.
- If the page needs to shrink: cut the "toolset and legend" highlight first (it's the one feature-tour item that's
  pure show-and-tell with no Python-side API novelty beyond `show_control()`/`add_legend()`), or fold
  "driving from inputs" and "fly_to from a worker thread" into a single side-by-side snippet+screenshot (they're
  already presented as a pair in "Updating the widget from Python").
- The comparison paragraph in the intro (GIS-app vs. programmatic-map framing) is short and, I think, the most
  important sentence in the whole page for someone deciding whether to use this widget at all -- keep it even in
  a trimmed version.

## Dropped from the old report (`docs/widget-reports/geolibre/report.md`)

- The PR-review framing entirely (scorecard, ranked findings, "merge-readiness") -- that report reviewed an
  unmerged PR; the integration has been on main for a while now and most of its findings are either fixed
  (local-file layers, blocking methods) or already folded into this guide's Gotchas as current, verified facts.
- The deployment addendum's reverse-proxy verification table (local vs. prefix-stripped-proxy iframe src) -- that
  level of infrastructure detail belongs in shinywidgets' own test suite (and already lives there,
  `tests/playwright/render_geolibre/test_render_geolibre.py`), not in a widget-choice guide for app authors.
- The "upstream issue to file" follow-ups list (rename the `layout` trait, add async command methods, proxy
  mount) -- these were planning artifacts; the proxy mount shipped, the async-methods ask became the still-open
  PR #360 (covered above), and the `layout` rename remains an open upstream ask mentioned once in Gotchas rather
  than carried as a to-do list here.
- The multi-session isolation and Connect-deployment verification notes -- infrastructure-level claims better
  owned by the test suite than repeated in a teaching guide; the guide's Gotchas already states deployed apps
  work, which is the user-facing fact that matters here.

## Update 2026-11-11 (main @ 32ca7035)

### What changed and why

- **#360/#396 (the main substantive change for this guide):** the `shinywidgets[geolibre]` extra floor is now
  `geolibre>=3.6.0` (bumped from 3.5.2 in `pyproject.toml`), and 3.6.0+ ships `*_async()` variants of every
  blocking command method (`fly_to_async()`, `get_center_async()`, `to_image_async()`, ...). Rewrote the whole
  "Updating the widget from Python" command-methods section and `examples/09_fly_to_worker_thread.py` (renamed
  to `examples/09_fly_to_async.py`) to teach the async pattern directly -- `await map.widget.fly_to_async(...)`
  inside a `reactive.extended_task`, no `functools.partial`/`loop.run_in_executor()` -- matching the shipped
  `examples/geolibre/app.py` in the worktree, which already uses this pattern. Also simplified
  `examples/04_snapshot_export.py`'s download handler from `run_in_executor(None, map.widget.to_image)` to
  `await map.widget.to_image_async()` (verified a download handler can await it directly without an
  `extended_task`, since it isn't part of Shiny's reactive flush -- see Verification). Applied the same
  simplification to `gallery/template_city_explorer.py` (fly-to) and `gallery/showcase_density_dashboard.py`
  (PNG export).
- **Verified, not assumed, that `extended_task` is still required for the async variants in a
  `reactive.effect`.** Wrote a throwaway probe (`await glmap.widget.fly_to_async(...)` directly inside a plain
  async `@reactive.effect`, no `extended_task`) and confirmed it hangs indefinitely (the awaited coroutine never
  returns, even after 5+ seconds) -- the same deadlock the blocking variants raise an error for. The guide's new
  wording states this as directly verified, not inferred from the geolibre docstring (whose generic phrasing
  "directly inside an async Shiny for Python observer" reads as if it might work -- it does not, for a
  `reactive.effect` specifically, confirmed empirically).
- **Removed the stale "examples/geolibre/app.py has exactly this bug" gotcha.** #396 (found while writing the
  previous pass of this very guide, per the PR body) already fixed the shipped example's `fly_to_city` reading
  `input.city()` inside the `extended_task` body; re-read the current `examples/geolibre/app.py` and confirmed
  it already reads the input outside the task and passes it as an argument. Kept the general
  `extended_task`-can't-read-reactive-sources gotcha (still true and useful) but dropped the now-false claim
  that the repo's own example demonstrates it.
- Converted every `reactive_read(map.widget, "project")` to `map.read("project")` across `guide.md`, 2 example
  files, and 1 gallery app (`project` lives on the rendered `Map` itself; no child widgets in this guide).
  Renamed the "### Beyond callbacks: `reactive_read`" heading to "### Beyond callbacks: `.read()`". Dropped the
  now-unused `reactive_read` import everywhere. `accessors: []` unchanged (still correct: no accessors on
  `render_geolibre`).

### Verification

- `examples/09_fly_to_async.py` (new, replaces the deleted `09_fly_to_worker_thread.py`): ran in browser, picked
  San Francisco, clicked "Fly there": `fly_to_city.result()` returned `[-122.4, 37.8]` (via
  `get_center_async()`), and the map visibly shows San Francisco Bay at zoom 9 in the after screenshot. Fresh
  before/after screenshots taken and looked at (Read tool), replacing the stale worker-thread ones (renamed from
  `09_fly_to_worker_thread_*.webp` to `09_fly_to_async_*.webp`).
- `examples/04_snapshot_export.py` (edited): ran in browser, clicked "Download PNG", confirmed a real
  `map.webp` download fires (Playwright's `expect_download`). No on-screen text changed (same page title, same
  card header), so the existing `img/04_snapshot_export.webp` screenshot is still accurate -- not regenerated.
- `examples/07_reading_project_state.py` (edited): ran in browser; `map.read("project")` returned the full
  document on load (`center`, `zoom`, populated `bbox`, `layers: ["US States"]`) -- confirms the conversion
  works end to end. Did not additionally re-drive the pan gesture this pass (a canvas-selector mismatch in the
  verification script, not a product issue -- the existing before/after screenshots from the 2026-10-30 pass
  already show a real pan changing the read values, and the code path is unchanged other than the call syntax).
- `examples/10_viewport_to_chart.py`, `gallery/showcase_density_dashboard.py`,
  `gallery/template_city_explorer.py` (all edited): mechanical conversions
  (`reactive_read(map.widget, "project")` -> `map.read("project")`; `run_in_executor`/worker-thread `fly_to()`
  -> `fly_to_async()` in the existing `extended_task`; `to_image()` -> `to_image_async()`); not independently
  re-driven with a live gesture this pass beyond the `09`/`04` verification above, which exercises the identical
  code paths.

### Bugs found (2026-11-11)

None new. The one bug this guide previously reported against the shipped `examples/geolibre/app.py` (#396) is
confirmed fixed on current main.

## Update 2026-11-11 (Task 8b: "Large data" section)

Added `## Large data` directly after "Coordinating multiple views." This guide has no large-data story of its
own to measure (its intro already says so, pointing to lonboard and maplibre); the new section restates that
plainly and links both siblings' own `#large-data` sections plus the new
`articles/performance/article.md#three-approaches-to-large-data` anchor (Task 7, same wave -- unresolved until
that task lands, expected). No new example or screenshot needed. `check_docs.py --links` shows only that one
expected unresolved anchor; `--snippets` is unchanged from `BASELINE.txt` (the 10 pre-existing mismatches in
this guide, none touched by this edit).
