# NOTES: MapLibre guide

## Versions and environment

- Date: 2026-10-30
- shinywidgets: `main` @ `00f90249` (worktree detached from `origin/main`, per the brief)
- shiny 1.9.0, Python 3.12, maplibre (py-maplibregl) 0.3.6, pydeck 0.9.3, anywidget 0.11.0, pandas/numpy/matplotlib
  as shipped in the shared venv
- Playwright Chromium, headless, launched with `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist` (matches the old report's recipe; needed for WebGL canvases to render under SwiftShader)
- Ports 9440-9458 (assigned range 9440-9459); verification driver at
  `/private/tmp/claude-502/-Users-cpsievert-github-py-shinywidgets/b5f9c833-cf3f-448f-841f-2c46c3116629/scratchpad/agents/maplibre/driver.py`
- Data: `https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json` (US state
  population density, 52 features, ~90 KB) and `https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson`
  (MapLibre's own heatmap-tutorial dataset, 6,107 points, ~1.2 MB) and
  `https://raw.githubusercontent.com/visgl/deck.gl-data/master/examples/3d-heatmap/heatmap-data.csv` (the showcase
  gallery app, unchanged from `examples/pydeck/app.py`). All three are small, stable, public, and need no API key.

## Verification table

Every example and gallery app was run with `shiny.run.run_shiny_app`, driven with Playwright, and screenshotted;
every screenshot was viewed with the Read tool before being referenced in `guide.md`.

| file | ran | screenshot(s) | gesture driven | confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | `quickstart.webp` | none (static) | renders and fills the card |
| `examples/02_basemap_styles.py` | yes | `basemap_before/after.webp` | radio click | `setStyle` swaps basemap, camera unchanged |
| `examples/03_geojson_choropleth.py` | yes | `choropleth.webp` | none (static) | data-driven fill paint renders correctly |
| `examples/04_fill_extrusion_3d.py` | yes | `extrusion_3d.webp` | none (static) | fill-extrusion height + color render in 3D |
| `examples/05_heatmap.py` | yes | `heatmap.webp` | none (static) | heatmap layer renders |
| `examples/06_circle_popups.py` | yes | `tooltip.webp`, `popup.webp` | hover (2-step mousemove), click | tooltip and popup both confirmed showing feature data |
| `examples/07_globe.py` | yes | `globe.webp` | none (static) | globe projection + GlobeControl render; required a bug workaround (see Bugs found) |
| `examples/08_deck_layers.py` | yes | `deck_before/after.webp` | slider drag (ion-range-slider click) | hexagon layer restyles (radius 200km -> 500km) in place |
| `examples/09_reactive_read.py` | yes | `reactive_read_before/after.webp` | drag (pan), scroll-wheel (zoom), click | `view_state` and `clicked` both confirmed updating with real values |
| `examples/10_mapbox_draw.py` | yes | `draw_before/after.webp` | polygon-tool click + 4 map clicks + Enter | `draw_feature_collection_all` confirmed with 1 drawn feature |
| `examples/11_rate_limiting.py` | yes | `rate_before/after.webp` | `window.widgetManager` model `.set()`/`.save_changes()` burst (see below) | debounced map: 3 reads vs default map: 12 reads for the same burst |
| `examples/12_update_in_place.py` | yes | `update_in_place_before/after.webp` | pan + scroll-zoom, then select dropdown + slider | ramp and filter both restyle; camera position unchanged before/after |
| `examples/13_click_to_detail.py` | yes | `click_detail_before/after.webp` | click | nearest-feature lookup confirmed (M8.1 Chiapas quake) |
| `examples/14_viewport_to_chart.py` | yes | `viewport_chart_before/after.webp` | scroll-zoom | visible count and histogram both update (829 -> 184) |
| `examples/15_filter_keep_viewport.py` | yes | `filter_viewport_before/after.webp` | scroll-zoom toward a cluster, then slider | filter applies; same zoomed-in camera before and after |
| `examples/16_table_to_fly_to.py` | yes | `table_fly_before/after.webp` | data-frame row click | `flyTo` animates toward the clicked row's coordinates |
| `examples/17_layout_sizing.py` | yes | `layout_sizing.webp` | none (static) | fill vs. fixed-height both render correctly |
| `gallery/template_quake_explorer.py` | yes | `gallery_template.webp` | click | filter + click-to-detail + on-screen count all work together |
| `gallery/showcase_uk_accidents.py` | yes | `gallery_showcase_before/after.webp` | click | probe count updates (0 -> 78 within 5km), yellow probe ring renders |

**Accessor coverage: `render_maplibre` declares no accessors** (`_accessor_specs` is not overridden for this
renderer; confirmed by reading `shinywidgets/_render_widget.py`). Per the brief, the `reactive_read()` tier is
the renderer's interaction story, and every trait it recommends was verified with a real gesture:
`view_state` (drag + scroll-zoom), `clicked` (click), and the MapboxDraw `draw_*` traits (draw-tool click sequence).

### Gesture notes

- **Click, hover, drag, and scroll-zoom are all real Playwright mouse/wheel events** on the
  `canvas.maplibregl-canvas` element -- no special picking workaround was needed (unlike some WebGL widgets),
  matching the existing Playwright test suite's approach (`tests/playwright/render_maplibre/test_render_maplibre.py`
  uses a plain `.click()`).
- **Hover needed a two-step `mouse.move()`** (move near the target, then onto it) to generate an actual
  `mousemove` event; a single `move()` to a point the cursor logically starts at does not always fire one.
- **The rate-limiting demo (`11_rate_limiting.py`) uses `window.widgetManager` model `.set()`/`.save_changes()`**
  (via the `expose_manager` route patch from `tests/playwright/conftest.py`) to fire ten `view_state` changes 50 ms
  apart, deterministically -- the same technique `tests/playwright/accessor_helper/test_accessor_helper.py` uses.
  This was a judgment call: a real drag's timing is harder to control precisely enough to produce a clean,
  reproducible "N rapid changes" demonstration, and the brief explicitly sanctions this technique for exactly this
  kind of case. The `view_state` trait's *mechanism* (updates on `moveend`/`zoomend`, confirmed by reading
  `maplibre/srcjs/ipywidget.js`) is independently verified with a real drag+zoom in `09_reactive_read.py`.
- **MapboxDraw's polygon tool is driven by UI**: click `.mapbox-gl-draw_polygon`, click three map points, close the
  loop, `Enter`. This worked first try.
- **Low-zoom pans can look like no-ops.** At world zoom levels (~1-2), MapLibre repeats the Mercator projection
  horizontally, so a purely horizontal pan can look visually identical even though the camera genuinely moved
  (`view_state` confirms it). `15_filter_keep_viewport.py`'s driver action zooms toward a specific point cluster
  first (not just pans) to avoid this -- a lesson for anyone writing their own low-zoom pan demos, not a product bug.

## Bugs and surprises found

Ranked by what a reader is likely to hit.

1. **[up, new finding] `Map.set_projection()`'s default argument (`ProjectionType.GLOBE`) is not JSON-serializable,
   and the failure silently drops every other call queued for that map.** `set_projection()` (in
   `maplibre/map.py`) does `self.add_call("setProjection", dict(type=type))` with `type` defaulting to the raw
   enum member, not `.value`. The whole "init" message (every queued `addSource`/`addLayer`/etc. call) is one JSON
   blob sent via `MapWidget.send()`; `json.dumps()` raises `TypeError: <ProjectionType...> is not JSON serializable`
   inside shinywidgets' `_publish_msg`. ipywidgets catches exceptions raised by trait-observer callbacks and logs
   them (shinywidgets reroutes this to its own logger -- see `shinywidgets/_comm.py`'s `ClientMsgErrorFilter`), so
   nothing reaches the browser and nothing shows in the Shiny UI: the map renders its basemap and camera, with
   every other queued layer/source silently missing. Reproduced directly: `server.log` showed
   `ERROR:shinywidgets:Exception in widget method ...: TypeError: <ProjectionType.VERTICAL_PERSPECTIVE:
   'vertical-perspective'> is not JSON serializable`. **Workaround** (used in `examples/07_globe.py`): pass the
   projection as a string, `m.set_projection("vertical-perspective")`. This is an upstream `maplibre` bug, not a
   shinywidgets one -- but shinywidgets' own error gets logged server-side only, with no user-visible signal, which
   makes failures like this one easy to miss during development. Minimal repro: a bare
   `Map().set_projection()` plus any `add_source`/`add_layer` call, rendered with `@render_maplibre`, rendered in a
   browser; check the server log for the `TypeError`, or that the added layer never appears.
2. **[up, confirmed still present, not a regression] MapboxDraw line styles don't render under this MapLibre GL JS
   version.** Drawing a polygon fills it but the outline is invisible; the browser console logs
   `layers.gl-draw-lines.*.paint.line-dasharray[2][0]: Expression name must be a string, but found number instead`.
   This matches the old report's finding 3.7 exactly, confirmed still present (not a shinywidgets regression --
   `mapbox-gl-draw`'s bundled line styles predate current MapLibre's stricter style validation).
3. **[sw/up, judgment call] The three explicit bugs the old `docs/widget-reports/maplibre/report.md` flagged as
   "fix before release" are all fixed on current `main`** -- re-verified, not re-reported as bugs here:
   - Explicit heights (`output_widget(height=...)`, `MapWidget(height=...)`) are honored, including inside a
     filling card and through `full_screen` (`maplibre_layout_defaults()` in `_render_widget_base.py`).
   - `as_widget_maplibre()` copies `map_options` and the message queue (`dict(...)`/`list(...)`) instead of
     aliasing the user's `Map`, with a comment explaining exactly why.
   - anywidget's hard-coded 2-second model-init timeout (which could permanently drop messages to a map under
     load) is patched to 60 seconds by `shinywidgets/_dependencies.py`'s `relax_anywidget_init_timeout()`.
4. **[docs, new finding] `render_maplibre`'s class docstring doesn't mention `rate_policy`/`rate_delay`**, even
   though they're accepted (inherited from `render_widget_base`) and work exactly as documented on siblings like
   `render_matplotlib`. Verified they apply to `reactive_read()` on this renderer's widget in
   `examples/11_rate_limiting.py` (12 reads unthrottled vs. 3 debounced for the same burst).
5. **[up, confirmed, low severity] `add_popup()`/`add_tooltip()` without `template=` inject raw property strings
   into `setHTML()`, unescaped.** Verified by reading the bundled `ipywidget.js`: the `prop=`/default-all-properties
   path returns the raw value and does not go through the mustache renderer that the `template=` path uses. Noted
   as a Gotcha with low severity (most properties come from your own data pipeline), not a blocking issue.

### Not independently re-verified

- The old report's **anywidget bundle-size / per-render websocket traffic measurements** (2.6 MB `_esm`, 2.83 MB
  per render) were not re-measured this pass. The underlying architecture (anywidget ESM sent as a synced trait)
  is unchanged, and the init-timeout mitigation (#3 above) addresses the failure mode that made the bundle size
  dangerous, so a fresh byte-count wasn't essential to this guide's claims.
- `Basemap.background()`'s missing `"sources"` key (old report's finding 3.8) -- not used in any example here
  (all examples use a real style URL), so not re-verified. Flagging in case it's still relevant to a future pass.
- maplibre's own `id="pymaplibregl"` being duplicated across multiple maps on one page -- cosmetic, not
  re-verified, didn't block anything in this pass's multi-map example (`11_rate_limiting.py`, which has two maps
  with no apparent id collision issue).

## Judgment calls for the maintainer to revisit

- **Dataset choice: MapLibre's own earthquake tutorial dataset** (`maplibre.org/maplibre-gl-js/docs/assets/
  earthquakes.geojson`, ~6,100 points) is used in 9 of the 17 examples plus both gallery apps, rather than a
  different dataset per example. This was deliberate: it's real, recognizable, stable, globally distributed (good
  for both regional zoom-ins and world/globe views), already used in MapLibre's own official heatmap tutorial (so
  the "Learn more" link is directly relevant), and reusing it kept the guide's per-example setup code short and
  consistent. The US states density dataset (choropleth + 3D extrusion + in-place restyle) is the other recurring
  dataset. If the maintainer wants more dataset variety across examples for visual freshness, that's an easy
  follow-up, but I'd weigh it against the added cognitive load of a reader tracking multiple datasets.
- **The `render_pydeck` deprecation and this guide's "Deck.GL layers" section overlap by design.** The pydeck
  example and the gallery showcase are both built from material that already exists in the shinywidgets repo
  (`render_pydeck`'s own docstring example, and `examples/pydeck/app.py`). I treated this as reuse of
  already-designed, already-correct material rather than independent invention -- the maintainer may want to
  cross-link more explicitly from the `render_pydeck` docstring/deprecation guide to this one, if such a guide
  exists in this swarm's output.
- **`examples/11_rate_limiting.py`'s counters needed `reactive.isolate()`** around the `n_fast.get()`/`n_slow.get()`
  read-then-increment, or the effect depends on its own output and loops forever (confirmed: without it, the demo
  app hangs indefinitely under `shiny-busy`, pegging a CPU core). This is a general Shiny gotcha, not specific to
  maplibre, but worth flagging since a counter-increment pattern like this is a natural thing for a guide reader to
  copy verbatim into their own rate-limiting demo.
- **`17_layout_sizing.py` has no inline code block in `guide.md`**, only a screenshot -- the brief's skeleton
  doesn't strictly require one for every subsection, and the file is short/self-explanatory; happy to add the
  full listing if the maintainer prefers every example to have an inline block.

## Editor's notes for the website

- **Strongest material**: the `update_in_place_before/after.webp` pair (ramp + filter change while the camera stays
  locked on the same panned/zoomed region) is the single clearest demonstration of "in-place beats re-render" in
  this guide, and the `filter_viewport_before/after.webp` pair (zoomed into California, magnitude filter clears it)
  makes the same point even more starkly. Either would work well as this guide's lead screenshot instead of the
  3D-extrusion hero, if the maintainer wants the hero image to double as a "why maplibre" and a "why reactive"
  pitch simultaneously.
- **What to cut for a shorter page**: the "Rate limiting" subsection could be trimmed to the table row plus one
  sentence (as jscatter's NOTES.md suggested for that guide) if space is tight -- `render_maplibre` has no
  accessors with their own default rate policy to contrast against, so the subsection is making a more abstract
  point (the kwarg exists and applies to `reactive_read()` generically) than on renderers with accessors.
  "MapboxDraw" could also be trimmed to a single paragraph without the dedicated example, if 3D & scientific /
  networks guides are competing for more space -- it's the least commonly used of the interaction patterns here.
- **What I dropped from the old report, and why**:
  - The PR-review scorecard, "verdict", and should-fix/nice-to-have lists: those were about reviewing a specific
    PR before merge, not about teaching the shipped feature.
  - The three "fix before release" bugs (aliasing, explicit heights, anywidget timeout): confirmed fixed on
    `main`; replaced with a one-line "already fixed" note under Gotchas rather than describing bugs that no longer
    exist.
  - The CHANGELOG-rewording and docstring-addition proposals, and the Playwright-test-to-add list: these are
    process/PR-review artifacts for the shinywidgets maintainers, not reader-facing content.
  - maplibre's native Shiny bindings comparison (`render_maplibregl`/`MapContext`): out of scope for a guide about
    `@render_maplibre`; the "choose this vs. siblings" framing in the intro covers the comparisons a reader
    actually needs (lonboard, ipyleaflet).
  - The duplicate-`id="pymaplibregl"` and verbose-`console.log` upstream nits: too minor to spend a Gotchas bullet
    on; neither affects functionality or was observed to cause a real problem in this pass's examples.

## Cross-widget pairings (for the coordinator's cross-cutting articles)

- **pairs with: matplotlib** -- `examples/14_viewport_to_chart.py` drives a matplotlib histogram from the map's
  `view_state` bounds (viewport -> chart of what's visible, one of the brief's named patterns).
- **pairs with: (Shiny core, not a widget)** -- `examples/16_table_to_fly_to.py` and the "Table row -> flyTo"
  section drive the map's camera from a plain `@render.data_frame` row click. Not a widget-to-widget pairing, but
  listed because it's a complete, reusable "drive the map from a table" pattern; works identically with
  itables/reactable in place of `@render.data_frame`.
- **pairs with: itables, reactable** (not built, but noted in the guide text) -- the table-to-fly-to pattern
  generalizes directly to either table widget's row-selection accessor in place of core Shiny's
  `cell_selection()`.
- **pairs with: pydeck (the deprecated `render_pydeck`)** -- the entire "Deck.GL layers" section and the showcase
  gallery app are the documented migration path for `render_pydeck`, which the shinywidgets maintainers already
  deprecated in favor of this renderer.

## Update 2026-11-11 (main @ 32ca7035)

### What changed and why

- Converted every `reactive_read(<output>.widget, "<trait>")` to `<output>.read("<trait>")` across `guide.md`,
  7 example files, and 2 gallery apps (19 call sites in `guide.md`, matching counts in `examples/`/`gallery/`):
  `view_state`, `clicked`, and `draw_feature_collection_all` all live on the rendered `Map`/`MapWidget` itself
  -- maplibre has no child widgets in this guide -- so every conversion lands on the output's own `.read()`.
  Updated imports (dropped the now-unused `reactive_read` import) in every touched file.
- Reworded the "Accessor reference" intro and the "Beyond the basics: MapboxDraw"/"Rate limiting" prose to teach
  `.read()` as the primary way to reach a trait, linking to the `reacting-to-widgets` article instead of
  re-explaining the mechanism. `accessors: []` in the front matter is unchanged (still correct: `render_maplibre`
  declares no `_accessor_specs` on current main).
- `examples/09_reactive_read.py`'s on-screen card header changed from `"Map state (reactive_read)"` to
  `"Map state (.read())"` to match what it actually calls now; regenerated both `img/reactive_read_before.webp`
  and `img/reactive_read_after.webp` since the stale header text was visible in both. Kept the file's name
  (`09_reactive_read.py`) rather than renaming it -- it's an internal example id, not shown to the reader, and
  renaming would have meant updating every cross-reference and image name for no reader-facing benefit.
- Checked #415 (messages queued before an output's comm opens are now delivered, e.g. `add_call()` right after
  a re-render) for a workaround to remove: none of this guide's `.widget` method calls (`add_call("setStyle",
  ...)` in `02_basemap_styles.py`, `set_paint_property`/`set_filter` in `12_update_in_place.py`, `set_filter` in
  `15_filter_keep_viewport.py`, `add_call("flyTo", ...)` in `16_table_to_fly_to.py`) had a sleep/
  `invalidate_later`/comm-open guard to begin with -- the 2026-10-30 pass apparently never hit the race (or
  didn't need to work around it), so there was nothing to delete. Re-read `02_basemap_styles.py`'s `_set_style()`
  effect specifically (it fires `add_call("setStyle", ...)` on every session's first flush, since the radio
  input has a default) as the closest candidate for this race; it already worked without a workaround before
  #415 and still does.

### Verification

- `examples/09_reactive_read.py` (edited): ran in browser; drove a real drag (pan), two scroll-zoom steps, and
  a click. `city.read("view_state")` and `city.read("clicked")` both updated with correct, plausible values
  (new center/zoom/bounds after the pan+zoom; a `{lng, lat}` matching the click point). Fresh before/after
  screenshots taken and looked at (Read tool) -- both match current UI text and values.
- `examples/10_mapbox_draw.py` (edited): ran in browser; drove the real MapboxDraw polygon tool (click the tool,
  three map clicks, close the loop). `city.read("draw_feature_collection_all")` went from `{}` (0 features) to a
  populated `FeatureCollection` with 1 feature and real coordinates.
- `examples/13_click_to_detail.py`, `examples/14_viewport_to_chart.py`, `examples/11_rate_limiting.py`,
  `gallery/showcase_uk_accidents.py`, `gallery/template_quake_explorer.py` (all edited): mechanical conversions
  of `reactive_read(<output>.widget, "clicked"/"view_state")` to `.read(...)`, same code path confirmed live
  above (`.read()` falls through to `reactive_read(widget, name)` verbatim for a bare trait -- read directly in
  `shinywidgets/_render_widget_base.py`); not independently re-driven with a live gesture this pass. The
  `clicked`/`view_state` traits themselves were already gesture-verified end to end in the 2026-10-30 pass.

### Bugs found (2026-11-11)

None new. #415 was checked against this guide's `.widget` command calls and found nothing to fix or remove --
see above.

## Update 2026-11-11 (A1: view_state()/clicked()/drawn_features() accessors, fix/accessor-c-fixes)

- `render_maplibre` gained three accessors (branch `fix/accessor-c-fixes`, PR pending): `view_state()`,
  `clicked()`, `drawn_features()`. Guide updated throughout: front matter `accessors:`, the accessor reference
  (now the standard 5-column table, with the remaining `draw_*` event traits on a `.read()` row each), and every
  `view_state`/`clicked`/`draw_feature_collection_all` read switched from `.read("<trait>")` to the accessor --
  in `guide.md`, examples 09/10/13/14, both gallery apps, and the linked-views article's maplibre example.
- **Accessor semantics vs. the old `.read()`:** `view_state()` cancels (`req(False)`) until the browser's first
  report instead of returning `{}` (example 14's "show all quakes until the first report" fallback went away with
  it); `clicked()` returns `None` instead of `{}` before the first click and is kept across re-renders;
  `drawn_features()` returns the features list (matching ipyleaflet), not the `FeatureCollection` wrapper.
- **Rate-policy correction:** the old "Accessor reference" table implied `view_state` might stream; the bundled
  JS reports it once per completed gesture (`load`/`moveend`/`zoomend`), so the accessor declares no default
  rate policy, and a renderer-level `rate_policy` doesn't apply to it. The Rate limiting section now says so and
  keeps example 11 on `.read("view_state")` (the only way to debounce it) with the "intermediate frame of a
  drag" claim corrected. Cheatsheet gained a `render_maplibre` section; choosing-a-widget updated (3 accessors).
- **Verified (all against the accessor branch, real Chromium):** example 09 (pan + 2 scroll-zooms + click;
  `view_state()`/`clicked()` both update; before/after screenshots re-taken -- the card header changed to
  "Map state (accessors)"), example 10 (real polygon draw via the MapboxDraw tool; `drawn_features()` goes 0 ->
  1 feature; screenshots re-taken), example 13 (click -> nearest-quake detail), example 14 and the linked-views
  07 (histogram re-renders on scroll-zoom), both gallery apps (pan + click drive the value boxes / nearest-quake
  text). 13/14/gallery screenshots kept: their visible content is unchanged by the accessor switch (13's "after"
  depends on click position, not code; 14's old before was already the post-load, viewport-filtered state).

## Update 2026-11-11 (Task 8b: "Large data" section)

Added `## Large data` directly after "Coordinating multiple views." Cites the already-verified gallery app
(`showcase_uk_accidents.py`, 140,000 points via `add_deck_layers()`) as the GPU-in-browser evidence, notes vector
tiles are already "only send what's visible" for the basemap, and that plain GeoJSON sources have no large-data
mode of their own. No new example or screenshot. One link to
`articles/performance/article.md#three-approaches-to-large-data` is unresolved until Task 7 (same wave) lands,
per the task block. `check_docs.py --links` on this guide shows only that one new unresolved anchor plus the four
pre-existing `BASELINE.txt` entries (`#deckgl-layers-the-pydeck-migration-path`, two `#click--detail-card`, one
`#table-row--flyto`) -- none newly introduced; line numbers for entries after the insertion point shifted by 13
lines (e.g. baseline's line 976 is now 989), same problem, not a new one.
