# NOTES: lonboard guide

## Versions

- Date: 2026-10-30
- lonboard 0.17.0, geopandas 1.2.0, shapely 2.2.0, pyarrow 26.0.0, matplotlib 3.11.2
- plotly 6.9.0, itables 2.9.1 (for the two cross-widget pairings)
- shiny 1.9.0
- shinywidgets commit `00f90249` (2026-10-30), i.e. current `main` at the time of writing
- Playwright Chromium, default headless launch (no special WebGL flags needed -- lonboard renders
  fine headless on this machine, matching the existing `tests/playwright/render_lonboard` suite)

## Data

`geopandas.datasets` was removed in GeoPandas 1.0 (the brief's suggested "geopandas-bundled"
dataset no longer exists). Used Natural Earth 110m **populated places** (243 cities, with
`POP_MAX`/`LATITUDE`/`LONGITUDE`) and **admin-0 countries** (177 countries, with `GDP_MD`/
`POP_EST`) instead, fetched at runtime from a stable, commonly-used GitHub mirror
(`nvkelso/natural-earth-vector`). Both are public domain, small (~650-850 KB), and load in well
under a second. Every example and gallery app uses this real dataset rather than synthetic data,
per the coordinator's note to prefer real/recognizable data where possible; the one exception is
`04_geoarrow.py`, which intentionally uses small synthetic points because the point of that example
is the GeoArrow *construction path*, not the data itself.

## Verification table

| File | Ran | Screenshot | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a (static) | n/a |
| `examples/02_choropleth.py` | yes | yes | n/a | n/a |
| `examples/03_arcs.py` | yes | yes | n/a | n/a |
| `examples/04_geoarrow.py` | yes | yes | n/a | n/a |
| `examples/05_multilayer.py` | yes | yes | n/a | n/a |
| `examples/06_globe.py` | yes | yes | n/a | n/a (see bug below) |
| `examples/07_accessors.py` | yes | before/after | pan, click, bbox select | all 4: yes |
| `examples/08_reactive_read_layer.py` | yes | before/after | click each layer | per-layer `selected_index` via `reactive_read`: yes |
| `examples/09_restyle_in_place.py` | yes | before/after | slider drag, switch toggle | n/a (restyle, not an accessor) |
| `examples/10_fly_to.py` | yes | before/after | dropdown select | n/a |
| `examples/11_viewport_to_chart.py` | yes | before/after | pan + zoom | `view_state()`: yes |
| `examples/12_click_to_detail_card.py` | yes | before/after | click | `selected()`: yes |
| `examples/13_bbox_to_table.py` | yes | before/after | bbox select | `selected_bounds()`: yes |
| `examples/14_table_to_fly_to.py` | yes | before/after | itables row click | n/a (table drives map) |
| `examples/15_rate_limiting.py` | yes | yes (static) | pan (5x) | see note below |
| `gallery/template_city_explorer.py` | yes | before/after | click | `selected()`: yes |
| `gallery/showcase_world_dashboard.py` | yes | before/detail/after(fly)/restyle | click, dropdown, slider, switch | `view_state()`, `selected()`: yes |

**Accessor coverage, each confirmed with a real Playwright gesture:**
- `view_state()`: yes -- pan/drag in `07_accessors.py`, `11_viewport_to_chart.py`,
  `showcase_world_dashboard.py`
- `selected()`: yes -- click in `07_accessors.py`, `12_click_to_detail_card.py`,
  `template_city_explorer.py`, `showcase_world_dashboard.py`
- `selected_bounds()`: yes -- Select BBox click-click in `07_accessors.py`, `13_bbox_to_table.py`,
  `template_city_explorer.py`
- `clicked()`: yes -- click in `07_accessors.py` (the map click that also triggers `selected_index`
  also exercises `clicked()`, since both fire from the same gesture)

**Not independently re-verified this round** (documented as such in the guide, not asserted as
fact from the old report):
- `selected()`/`clicked()` not re-firing on an identical repeated pick/click -- this is
  generic `AccessorSpec(priority="input")` dedup behavior (the default, which lonboard's specs use
  unmodified), already covered by `tests/unit/test_accessors.py`'s `test_input_priority_ignores_equal_payloads`.
  Not re-clicked twice in a live browser for this guide specifically; stated in the guide as a
  property of the input-priority mechanism, not a lonboard-specific claim I re-derived from scratch.
  Documented in the docstring as fact; I treated the docstring claim as reliable here because it
  follows directly from code I read (`_lonboard.py` passes no `priority=` override, so it's the
  default "input").
- Experimental `TextLayer` crash (mentioned in the old report) -- not reproduced this round; dropped
  rather than carried forward unverified (see "Dropped from the old report" below).

## Bugs found

### shinywidgets / cross-cutting
None found this round that are specific to shinywidgets' lonboard integration. The `GlobeView`
issue and the percentage-height issue below are both triggered through shinywidgets but are
upstream lonboard problems (reproduced via a plain browser event / lonboard's own CSS, nothing
shinywidgets-specific).

### Upstream (lonboard)

1. **`GlobeView` breaks `view_state()` -- regression-equivalent, high-impact for anyone who tries
   GlobeView + accessors.** The browser always serializes the full view-state shape (including
   `pitch`/`bearing`) when syncing to Python, but `lonboard.view_state.GlobeViewState` has no
   `pitch`/`bearing` fields (confirmed via `dataclasses.fields`). The very first sync after a
   `GlobeView` map renders throws `TypeError: GlobeViewState.__init__() got an unexpected keyword
   argument 'pitch'` inside ipywidgets' `Widget._handle_msg` -- caught and logged by ipywidgets
   itself (doesn't crash the app), but it means the trait update is silently dropped, so
   `view_state()` (the accessor) and any `reactive_read(map.widget, "view_state")` never update for
   a globe map again after that first failed sync. Minimal repro: `examples/06_globe.py` as
   written -- just rendering it reliably throws this in the server log (no gesture needed; it fires
   on the initial auto-fit sync). Reported in the guide's Gotchas section. Not something
   shinywidgets can work around without papering over lonboard's own trait validation.
2. **`Map(height="50%")` silently renders a 0-height map.** Confirmed still present on lonboard
   0.17.0 (minimal repro: `probes/pct_height.py` in scratch, measuring `.lonboard`'s
   `getBoundingClientRect()` -- `{width: 1232, height: 0}`). lonboard's own CSS gives the root
   element `min-height: 100%`, which resolves to `0` once the parent isn't a definite height (the
   `fill=False` / non-pixel-height path). Long-standing limitation, not a regression; carried
   forward from the old report since it still reproduces.
3. (Old report claim, re-verified and **dropped as stale**) "Changing `basemap` after a fly-to
   desyncs `view_state`." Built a minimal repro (`probes/basemap_check.py`): pan, then toggle
   `basemap`, then compare the accessor's reported `view_state()` against the actual rendered map
   position. On current `main` (lonboard 0.17.0) the view does **not** reset and `view_state()`
   stays accurate -- screenshot matches the printed coordinates exactly. This appears to have been
   fixed upstream since the earlier report (PR #299 era). Not included in the guide's Gotchas.

## Judgment calls for the maintainer to revisit

1. **Accessor-subsection structure.** Rather than one example file per accessor, I used a single
   combined app (`07_accessors.py`, modeled directly on the existing
   `tests/playwright/lonboard_accessors/app.py` fixture) for the "Accessor reference" subsections,
   and reserved separate, fuller example files for the "Coordinating multiple views" section. This
   avoids four near-duplicate single-accessor demos. If the website wants one code sample per
   accessor subsection instead, that's a quick split of `07_accessors.py`.
2. **Rate limiting section is mostly explanatory, not demonstrative.** I verified precisely that
   `rate_policy`/`rate_delay` have zero effect on any of the four accessors (via direct inspection
   of `render_lonboard(...)._accessors._slots[...].limiter`, all `None` regardless of kwargs
   passed -- this matches `tests/unit/test_accessors.py`'s `test_override_policy_ignored_without_a_default`).
   I could not get a convincing *visual* before/after of the throttle actually slowing
   `reactive_read()` down, because my scripted pan gestures (with Playwright's per-step overhead)
   already run slower than the 1-second throttle window I set -- so the screenshot shows both
   readouts agreeing, which is accurate but not dramatic. Happy to revisit with a tighter rate_delay
   or a faster synthetic trait-write loop if the maintainer wants a more visually convincing proof.
3. **GlobeView kept in "What you can build" despite the `view_state()` bug.** I judged the visual
   (a legitimate WebGL globe, one line of code) worth keeping as a feature highlight, with the bug
   called out both inline under the example and in Gotchas, rather than cutting GlobeView
   entirely. Reasonable people could cut it until the upstream bug is fixed, since any app that
   reads `view_state()` on a globe map is silently broken.
4. **Hero image doubles as a gallery screenshot** (`gallery_showcase_world_dashboard_detail.webp`).
   I didn't shoot a separate, cropped hero image; this one is also used as the showcase's main
   screenshot. If the website wants a dedicated, more tightly cropped hero, it's a 2-minute
   re-shoot from `gallery/showcase_world_dashboard.py`.

## Operational note (not about the guide content)

Partway through this session, the shared main checkout's `pyproject.toml` and
`shinywidgets/_render_widget.py` intermittently contained live git merge-conflict markers (another
session appeared to be cherry-picking a mols2grid port onto a different branch in the same
checkout), which broke `uv run` for several minutes at a time. The coordinator redirected me to an
isolated worktree (`scratchpad/main-wt`, detached at `origin/main`) for all `uv run` invocations
partway through; I did so for the remainder of the session. All `docs/widget-guides/lonboard/`
output is unaffected (it's git-excluded and lives in the main checkout regardless of which branch
that checkout has loaded). Flagging in case other agents hit the same thing.

## Editor's notes for the website

- **Strongest material:** the "Coordinating multiple views" section (viewport->chart,
  click->detail, bbox->table, table->fly-to) is the most convincing part of this guide and probably
  the best advertisement for lonboard+accessors in the whole roster -- four complete, different
  interaction directions, all from the same four accessors.
- **Strongest screenshot:** `gallery_showcase_world_dashboard_detail.webp` (choropleth + sized city
  layer + detail card) -- used as both the hero and the showcase shot.
- **Candidate for cutting in a shorter page:** the GeoArrow-table example (`04_geoarrow.py`) is the
  least visually distinctive (it's just more pink dots) -- its value is entirely in the code, not
  the screenshot. Could be reduced to a code snippet with no image if space is tight.
- **Candidate for cutting:** the `08_reactive_read_layer.py` subsection is useful but narrow
  (multi-layer picking is an edge case). Could be folded into a single sentence with a link to the
  example file instead of a full code block + before/after pair.

## Cross-widget pairings (for the coordinator's cross-cutting articles)

- **pairs with: plotly** -- `examples/11_viewport_to_chart.py` (map viewport drives a plotly bar
  chart of what's visible)
- **pairs with: itables** -- `examples/13_bbox_to_table.py` (box selection drives a filtered
  itables table) and `examples/14_table_to_fly_to.py` (the reverse: an itables row selection flies
  the map camera)

## What I dropped from the old report, and why

- **The "magic tricks" / scoring table framing** -- the old report was a PR review with a
  ★-rating table; this guide is teaching material, so I replaced it with direct "what you can
  build" / "coordinating views" sections instead of a review scorecard.
- **The draw-a-box-tool UX complaint and the pan/zoom-as-selection workaround it motivated** -- the
  old report spent significant space on why it dropped lonboard's built-in Select BBox tool in
  favor of viewport-bounds-as-selection. I kept *both* techniques in this guide (Select BBox genuinely
  works fine for a bbox-to-table pattern; viewport-bounds is a separate, additional technique for
  continuous "what's visible" filtering) rather than treating one as a workaround for the other.
- **The experimental `TextLayer` crash and the ArcLayer-world-view note** -- `TextLayer` not
  reverified this round (dropped rather than carried forward unverified, per "verify every claim in
  a browser" instruction); the ArcLayer-no-geometry note is folded directly into the `03_arcs.py`
  example's own comment instead of a separate Gotchas bullet, since it's precisely the reason that
  example sets an explicit `view_state`.
- **The `basemap` desync bug** -- re-verified and found fixed upstream; see "Bugs found" above.
- **The categorical-color-via-continuous-ramp and concave-hull cluster-outline techniques** -- both
  are good ideas but were written for a specific 200k-point synthetic NYC dataset the old report
  built; I used `apply_continuous_cmap` directly against a real `GDP_MD`/`POP_MAX` column instead,
  which demonstrates the same API more simply against real data.
- **The shipped `examples/lonboard/app.py`** -- still uses `reactive_read()` + manual
  `.observe()`-equivalent patterns predating the accessors; I didn't touch it (out of scope: the
  brief's sources of truth are `main`'s current state, not a mandate to migrate the shipped
  example), but flagging that it's a visible inconsistency a user will notice if they read both the
  example and this guide side by side.

## Update 2026-11-11 (main @ 32ca7035)

Updated against `main` @ `32ca7035` (33 commits since the `00f90249` baseline this guide was
originally written against), per the coordinator's update brief. shinywidgets commit used for
verification: `32ca7035`; lonboard 0.17.0 (unchanged), shiny 1.9.0 (unchanged).

### What changed in the guide, and why

- **Accessor reference table**: replaced the `Fires when`/`None means` columns with `Before any
  interaction` / `Across re-render`, per the new brief. `view_state()` now shows "Debounced, 250
  ms" (was "None") and `selected()`/`selected_bounds()`/`clicked()` now show their
  before/across-re-render behavior explicitly instead of a blanket "events reset to None" rule.
- **Deleted the event/state taxonomy.** The old guide said `view_state()` is a "state" accessor
  and the other three are "events" that reset to `None` on re-render. That's no longer accurate
  (or the right framing): `view_state()`/`selected()`/`selected_bounds()` are **re-seeded**
  from the new map (usually to the same `None`/seeded-value outcome a reader would have seen
  before, but for the right reason -- the map is immutable, so a new render starts from the new
  map's own state), while `clicked()` is now **kept** across a re-render. Rewrote the per-accessor
  subsections and the reference table around "before interaction" / "across re-render" instead of
  "event" vs "state".
- **`clicked()` no longer resets on re-render.** Verified directly (script below): click the map,
  force a re-render via a button, and the previous click's coordinates are still there --
  previously (pre-#437) this reset to `None` on every re-render since `clicked` was declared as an
  "event" accessor. Also corrected the stale claim that reading `clicked()` is what makes the
  browser report clicks ("the first read flips `_has_click_handlers`, registering the listener
  lazily"): `clicked()` now attaches unconditionally at render, like every other accessor; there
  was never a `listen_to` kwarg to remove (none existed in this guide or in `_lonboard.py`).
- **`view_state()` debounces by default now (#400), and the docstring no longer claims it reports
  only at settle.** The old guide attributed the ~300 ms pacing to lonboard's own browser-side
  debounce. On current `main`, the accessor's own docstring says the browser reports continuously
  through the gesture and shinywidgets debounces the *accessor's* publication to Python at 250 ms
  by default (`AccessorSpec(rate_policy="debounce", rate_delay=0.25)` in `_lonboard.py`). This also
  means `render_lonboard`'s `rate_policy`/`rate_delay` kwargs now reach `view_state()` itself, not
  just `reactive_read()` on other traits -- rewrote the "Rate limiting" section and its example
  around this (see below). Softened the old "zoom lags 2-4 seconds" claim to a mechanism-level
  statement (each frame re-arms the debounce) rather than a specific duration, since I didn't
  re-measure exact timing under the new mechanism and don't want to assert an unverified number.
- **`selected()`/`selected_bounds()` are re-seeded.** Functionally this looks the same as
  before for an ordinary (non-`shared_lifetime()`) map -- both go back to `None` on re-render --
  but the *reason* changed (re-seeded from the new map's own state, not hard-reset because of an
  "event" kind), and the docstring's nuance about a `shared_lifetime()` map potentially retaining a
  pick across its own re-renders is new. Added that nuance to the `selected()` subsection.
- **Rate limiting section and example rewritten.** The old section's entire premise ("none of the
  four accessors has a default rate policy") is now wrong for `view_state()`. Replaced the
  `reactive_read(map.widget, "view_state")` vs. `map.view_state()` comparison (which no longer
  demonstrates anything, since they're now the same accessor call) with a `rate_delay=0` example
  that shows `map.view_state()` and `map.read("view_state")` agree, and explains that `rate_delay`
  now also controls `view_state()`'s own debounce. New example file: `examples/15_rate_limiting.py`
  (verbatim match with `guide.md`, verified). Also updated the `## Learn more`-adjacent prose and
  the `selected()`/`clicked()` subsections to reference `reactive_read()` for layers while
  explaining *why* (a layer is a child widget, not the output's own `.widget`, so there's no
  `.read()` for it) per the update brief's instruction to say why `reactive_read()` is still used
  for child widgets.
- **`.read()` tier-2 usage**: no `reactive_read(map.widget, "<trait>")` calls remained in this guide
  after the rate-limiting rewrite (the only one was on `"view_state"`, itself an accessor name, so
  it's now `map.read("view_state")`/`map.view_state()`). The two remaining `reactive_read()` calls
  in the guide are both on a *layer* (`08_reactive_read_layer.py`), a child widget, which is the
  correct tier-3 usage and is called out as such.

### New/edited examples, verification status

- `examples/15_rate_limiting.py` -- rewritten. Ran on port 8512 in the worktree; drove a real
  pan gesture with Playwright (mouse down/move-steps/up), confirmed the coordinates update with no
  perceptible lag (`rate_delay=0`) and that `map.read("view_state") == map.view_state()` on every
  read, before and after the pan. Screenshot taken and looked at (`img/15_rate_limiting.webp`,
  replaces the stale one that showed the old throttle/reactive_read comparison).
- No other example files changed -- `07_accessors.py` through `14_table_to_fly_to.py` and the
  gallery apps are unaffected by the accessor redesign (their code already matched post-redesign
  behavior; only the prose around them needed correction). Not re-run this round except
  `06_globe.py`, re-verified below.
- Re-verified `clicked()`-kept-across-re-render and `selected()`/`selected_bounds()`-re-seeded
  with a throwaway probe app (not committed to `examples/`, per "scratch/throwaway drivers go in
  scratch, not the guide dir"): a map with an action button that re-renders it, plus text outputs
  for all three accessors. Click the map, Select-BBox a box, click "Re-render", and read all three:

  ```
  after bbox:              clicked=(20.66, 39.66)   picked=4   bbox=(17.83, 39.66, 20.66, 40.34)
  AFTER RERENDER:           clicked=(20.66, 39.66)   picked=None  bbox=None
  ```

  Confirms exactly the brief's claim: `clicked()` kept, `selected()`/`selected_bounds()`
  re-seeded to `None`.
- Re-verified `GlobeView` breaking `view_state()` (`06_globe.py`) still reproduces on current
  `main`: server log shows the same `TypeError: GlobeViewState.__init__() got an unexpected
  keyword argument 'pitch'` on first render. Carried forward in Gotchas unchanged (still an
  upstream lonboard bug, not a shinywidgets regression).
- Verified `view_state()`'s default rate policy directly via object inspection (not a timing
  screenshot -- see "Judgment calls" below):
  ```python
  from shinywidgets import render_lonboard
  r = render_lonboard(lambda: None)
  r._accessors._slots["view_state"].limiter._policy, r._accessors._slots["view_state"].limiter._delay
  # ('debounce', 0.25)
  r._accessors._slots["selected_index"].limiter  # None
  r._accessors._slots["clicked"].limiter          # None
  ```
  And with `render_lonboard(rate_policy="throttle", rate_delay=1.0)`, `view_state`'s limiter
  becomes `('throttle', 1.0)` while the other three stay `None` -- confirms the renderer's kwargs
  now reach `view_state()`'s own debounce, not just `reactive_read()` on other traits.

### Accessor coverage (each confirmed with a real gesture)

Unchanged from the original round -- all four (`view_state()`, `selected()`,
`selected_bounds()`, `clicked()`) were already verified with real Playwright gestures in
`07_accessors.py` and the other examples; this round added the re-render-specific verification
above (click/select, then re-render, then re-read) on top of that.

### Bugs found this round

None new. The `GlobeView` bug (upstream lonboard) still reproduces; no shinywidgets-specific bugs
found in the lonboard integration on current `main`.

### Judgment calls for the maintainer to revisit

- **Rate-limiting section: dropped the live before/after timing demo.** I considered a two-map
  side-by-side (default-debounced vs. `rate_delay=0`) with update counters to visually prove the
  debounce is coalescing updates, but in this headless/swiftshader environment the browser's own
  frame-paint cadence during a scripted gesture was slow enough that both counters came out equal
  (2-3 updates each) regardless of the Python-side rate policy -- the limiter never got a chance to
  coalesce anything because raw emits already arrived slower than the debounce window. This is the
  same limitation the original round's NOTES.md flagged for the old throttle/reactive_read demo
  ("my scripted pan gestures already run slower than the throttle window I set"). I verified the
  mechanism directly via object inspection instead (see above) and kept the example to something
  that *is* reliably demonstrable in a screenshot: `rate_delay=0` giving a live, lag-free readout,
  plus the `read()`/accessor-method equivalence. Happy to revisit with a different gesture-driving
  approach (e.g. writing trait values directly via `window.widgetManager` instead of simulated
  mouse events) if the maintainer wants a dramatic visual.
- **Didn't add a dedicated "read on demand" example for lonboard.** The update brief calls this out
  explicitly for ipyleaflet/leafmap (`bounds()`/`drawn_features()` in a button handler), not
  lonboard. lonboard's accessors already attached eagerly at render before this redesign too (they
  were already `kind="state"`, which always attached at render -- only `clicked()`'s *kind*
  changed, from "event" to being treated as kept), so "read on demand now just works" is a smaller
  incremental story here than for the ipyleaflet-family guides. The `12_click_to_detail_card.py`
  and `13_bbox_to_table.py` examples already demonstrate reading `selected()`/
  `selected_bounds()` safely with `req()` regardless of when the interaction happened, which covers
  the same ground. Flagging in case the maintainer wants an explicit "Save view" button example
  added for parity with the other map guides.

## Update 2026-11-11 (B1 rename: selected_index() -> selected())

- The primary selection accessor was renamed to `selected()` (one rule across renderers; unreleased API, no
  shims). Guide, examples, and front matter updated; widget *trait* names (e.g. jscatter's `selection`,
  lonboard's layer `selected_index`, ipyaladin's `_selected_objects`) are unchanged, and references to those
  or to upstream widget methods (`plot.value.selection()`, `EmbeddingAtlasWidget.selection()`,
  `Aladin.selection()`) were deliberately left alone.
- `img/07_accessors_*.webp` re-shot. The `_slots["selected_index"]` line in the 2026-10-30 verification
  transcript above is historical; the slot is now named `selected`.

## Update 2026-11-11 (Task 8b: "Large data" section)

Added `## Large data` directly after "Coordinating multiple views." Reuses
`articles/performance/article.md#2-big-data-choosing-the-right-widget`'s existing measured bytes/time for
lonboard at 10K/100K/1M points (25.2 MB, 3.1 s at 1M) rather than re-measuring -- that table already exists and
is in scope for Task 7 (same wave), not this task. No new example or screenshot. One link to
`articles/performance/article.md#three-approaches-to-large-data` is unresolved until Task 7 lands, per the task
block; `check_docs.py` on this guide is otherwise clean.

## Update 2026-11-11 (B2: selected_rows(), lonboard)

- New accessor `map.selected_rows(df=None)`: the picked row of a data frame. `df` defaults to a frame
  rebuilt from the pickable layer's own data (`geopandas.GeoDataFrame.from_arrow(layer.table)` -- keeps
  rows/columns, fresh `RangeIndex`, needs geopandas, which is deliberately NOT in the
  `shinywidgets[lonboard]` extra; a clear `ImportError` otherwise, and `df=` always works). Every lonboard
  layer has a `selected_index` trait (image layers included), so the default requires exactly one layer
  and raises otherwise (the pick has no layer identity). Implemented in the `b2-lonboard-selected-rows`
  worktree, stacked on `b2-bqplot-selected-rows` (PR pending).
- Front matter `accessors:` list, intro paragraph, and the accessor reference table all gained
  `selected_rows()`. New subsection "`selected_rows()`" after `selected()` (default frame + RangeIndex
  note, one-pickable-layer requirement, geopandas note, positional caveat); `selected()`'s prose no
  longer teaches `gdf.iloc[map.selected()]` for the rows use case. The "Click a city, see a detail card"
  pattern is now "`selected_rows()` plus `req()`".
- Examples switched from hand-rolled `index = req(map.selected()); row = ....iloc[index]` to
  `selected_rows()`: `examples/12_click_to_detail_card.py` (default frame -- no second read of the
  GeoJSON), `gallery/template_city_explorer.py` (default frame), and
  `gallery/showcase_world_dashboard.py` (`selected_rows(cities())` -- two pickable layers, so the frame
  is passed explicitly; the choropleth's `PolygonLayer` is pickable too). `07_accessors.py` (raw
  accessor readout), `08_reactive_read_layer.py` (per-layer picks), and `14_table_to_fly_to.py`
  (itables drives the map) unchanged on purpose.
- Cross-cutting articles updated: cheatsheet (new `selected_rows()` row under render_lonboard),
  reacting-to-widgets "Rows of your data" (lonboard added to the list + a bullet), choosing-a-widget
  matrix (accessor count 4 -> 5), linked-views (example 03 re-synced verbatim with
  `12_click_to_detail_card.py`, code block + caption, and the "Selection -> table of rows" library
  list).

Verification (all against the B2 worktree's code, real click gestures, screenshots looked at):

| File | Ran | Screenshot looked at | Gesture | Accessor confirmed |
|---|---|---|---|---|
| `examples/12_click_to_detail_card.py` | yes | yes (before/after re-shot) | scan-click near Paris estimate | `selected_rows()` default: card "Warsaw / Poland / Population: 1,707,000" |
| `gallery/template_city_explorer.py` | yes | yes (before/after re-shot) | scan-click | default: "Belgrade / Serbia / Population: 1,099,000" |
| `gallery/showcase_world_dashboard.py` | yes | yes (before/detail re-shot) | scan-click | `selected_rows(cities())` with two pickable layers: "Vienna / Austria" |
| `articles/linked-views/examples/03_lonboard_click_to_detail.py` | yes | yes (before/after re-shot) | scan-click | default: "Warsaw / Poland / Population: 1,707,000" |

No new bugs found. Driving note for future agents: `window.__deck` (lonboard's exposed deck instance)
has a null `viewManager` on these pages, so deck-side projection/picking isn't available; the working
gesture is a scan of real clicks ordered by a Web Mercator estimate of the target city (hits within
1-2 clicks at 12 px steps over a world-fit map).
