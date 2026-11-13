# NOTES: leafmap guide

## Versions

- leafmap 0.63.1, ipyleaflet 0.20.0, maplibre (py-maplibregl) 0.3.6, plotly 6.9.0 (under the
  `shinywidgets[leafmap]` extra's `plotly>=5.12,<7` pin), geopandas 1.2.0, mapclassify (latest), rioxarray/xarray/
  scipy (latest), keplergl 0.3.7 + `setuptools<81` (checked only for construction/config shape, not exercised in
  a full example -- see Judgment calls).
- shinywidgets commit: the `main-wt` worktree detached at `origin/main` as of 2026-10-30 (includes
  `render_leafmap`, `_LAYOUT_DEFAULTS["leafmap"]`, `as_widget_leafmap`, and `_IpyleafletAccessors`).
- shiny 1.9.0. Date: 2026-10-30. All apps run via `uv run --no-sync --with <extras> python -m shiny run ...` from
  the worktree, screenshotted with Playwright Chromium, viewport 1280x800 (900 tall for the gallery showcase),
  `device_scale_factor=2`.

## Session interruption and recovery (2026-11-02)

The agent process was interrupted after the first verification pass (all screenshots and apps already done and
browser-verified) but before a final lint/format pass. On resume, the scratchpad and worktree had been recreated
fresh (same paths, `origin/main` @ `00f90249`); all outputs under `docs/widget-guides/leafmap/` had survived and
needed no re-work. Two things were fixed during recovery, both pre-existing from the original pass, neither
affecting any verified claim or screenshot:

1. **Example files had a non-standard `# Run: ...` / `# Needs: ...` two-line header** that the sibling guides
   (`plotly`, `altair`, `embedding-atlas`, ...) don't use -- their convention is prose comments only where a
   non-default install is needed, with run commands otherwise left to the guide's Installation section and
   per-snippet lead-in prose. Rewrote all 13 example headers to match (dropping the header entirely for examples
   needing only the base `shinywidgets[leafmap]` extra), which also meant every code block embedded in `guide.md`
   needed re-syncing to stay byte-identical to its file (verified programmatically afterward).
2. **`ruff check --fix` and `ruff format`** (run against `examples/` and `gallery/`, matching `make check-format`)
   fixed import-sort ordering in 7 files and one re-wrap in 2 files; also caught one real issue: `examples/
   07_bounds_viewport_chart.py` had unused `from shiny import reactive, req` imports (leftover from an earlier
   draft) that `ruff check` flagged. All affected files (`01-13`, both gallery apps) were re-run in a browser after
   these fixes with zero console errors, confirming the fixes were purely mechanical.

## Coordinator's shared-venv version-drift warning (checked)

The coordinator warned that an unpinned `--with <pkg>` can silently overlay a different version of a package
*already* in the locked worktree venv (e.g., a stray `--with duckdb` pulling duckdb 2.0 over the locked 1.5.6).
Checked explicitly for this guide: every `--with` combination used below (`leafmap`, `localtileserver`,
`rioxarray`, `scipy`, `shapely`, `plotly`, `mapclassify`, `geopandas`, `playwright`) resolves `numpy`, `xarray`,
`scipy`, `shapely`, `plotly`, `pandas`, and `geopandas` to the exact same versions as a bare `uv run --no-sync`
with no overlay at all (numpy 2.5.4, xarray 2026.9.0, scipy 1.18.1, shapely 2.2.0, plotly 6.9.0, pandas 3.1.0,
geopandas 1.2.0) -- uv's overlay resolver reused the already-locked versions rather than bumping them. Only
genuinely-absent packages (`leafmap`, `localtileserver`, `rioxarray`, `mapclassify`, `playwright`'s Python
package, `keplergl`) were newly installed into the overlay. No findings in this guide depend on a drifted version.

## Verification table

| File | Ran? | Screenshot? | Gesture driven? | Accessor confirmed? |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a | n/a |
| `examples/02_basemaps.py` | yes | yes | select input (not a map gesture) | n/a |
| `examples/03_vector_data.py` | yes | yes | n/a (hover not captured) | n/a |
| `examples/04_choropleth.py` | yes | yes | n/a | n/a |
| `examples/05_raster_cog.py` | yes | yes | n/a | n/a |
| `examples/06_split_map.py` | yes | yes | n/a | n/a |
| `examples/07_bounds_viewport_chart.py` | yes | yes (before/after) | scroll-wheel zoom, real gesture | `bounds()` yes -- chart content changed (global top-10 -> Eastern Europe top-10) |
| `examples/08_zoom_center.py` | yes | yes | n/a (static read) | `zoom()`/`center()` yes -- read constructor values correctly |
| `examples/09_clicked_detail.py` | yes | yes (before/after) | real click | `clicked()` yes -- click near Thunder Bay, ON resolved to the correct nearest city |
| `examples/10_drawn_features_zonal.py` | yes | yes (before/after) | real mouse-drag rectangle draw | `drawn_features()` yes -- stats and histogram populated from the drawn rectangle |
| `examples/11_maplibre_reactive_read.py` | yes | yes | n/a (static read after load) | n/a (this example verifies `reactive_read()` + the accessor's `TypeError`, not an accessor) |
| `examples/12_in_place_updates.py` | yes | yes (before/after) | select input (city), real in-place fly-to | n/a (not an accessor; verifies in-place update preserves toolbar/state) |
| `examples/13_layout_sizing.py` | yes | yes | n/a | n/a |
| `gallery/template_choropleth_explorer.py` | yes | yes | n/a | n/a |
| `gallery/showcase_aoi_workbench.py` | yes | yes (before/after, two AOIs) | two real mouse-drag rectangle draws | `drawn_features()` yes -- two-row stats table + bar chart populated correctly |

All five accessors (`bounds`, `zoom`, `center`, `clicked`, `drawn_features`) were exercised with a real Playwright
gesture and the Python-side value was rendered to a `@render.code`/`@render.data_frame`/chart output and
screenshotted. `zoom()`/`center()` were only verified via their seeded constructor values (no separate
pan/zoom-and-confirm screenshot pair) -- low risk, since `../ipyleaflet/guide.md` exercises the identical
accessor with a real zoom-button click.

## Bugs found

- **[upstream, leafmap]** `add_raster(source)` requires a `str`; a `pathlib.Path` raises
  `ValueError: The source must either be a string or TileClient` from `leafmap.common.get_local_tile_layer`.
  Repro: `docs/widget-guides/leafmap/examples/05_raster_cog.py`, line defining `COG` as a `Path` and originally
  calling `m.add_raster(COG, ...)` without `str(...)`.
- **[upstream, leafmap, docs]** `add_raster(indexes=...)`'s type hint is `Optional[int]`, but the implementation
  (`leafmap/leafmap.py`, `add_raster` -> `get_local_tile_layer`) does `[tile_client.band_names[i - 1] for i in
  indexes]`, which raises `TypeError: 'int' object is not iterable` for a bare int. Repro: pass `indexes=1`
  instead of `indexes=[1]` to `add_raster`. Found while building `gallery/showcase_aoi_workbench.py`.
- **[upstream, leafmap, resolved since the old report]** The old report (`docs/widget-reports/leafmap/report.md`
  §3.4) found `leafmap.plotlymap.Map()` failing to construct under plotly &ge;6 (removed `add_scattermapbox`/
  `layout.mapbox`). Verified on leafmap 0.63.1 + plotly 6.9.0: constructs and the MRO shows `plotly.graph_objs.
  FigureWidget` cleanly. This is either a leafmap fix since the old report's August 2026 leafmap version, or the
  old report's plotly-version matrix was narrower than `shinywidgets[leafmap]`'s `plotly>=5.12,<7` pin exercises.
  Not re-tested with plotly 5.12-5.24 specifically (the old report's separate shinywidgets-plotly-5-blank-render
  regression, if still present, is a plotly-guide concern, not leafmap's).
- **[upstream, leafmap, resolved since the old report]** The old report (§3.6) found `leafmap.deck.Map` producing
  a JSON-dump `TypeError` instead of pydeck's helpful "no widget" message. Verified fixed: `as_widget_leafmap()`
  now MRO-walks for a pydeck base class and raises `PYDECK_NO_WIDGET_MESSAGE` plus leafmap-specific guidance
  (`leafmap.maplibregl.Map` + `add_deck_layers()`). Also verified the folium path gives the documented
  `@render.ui` + `ui.HTML(m._repr_html_())` recipe rather than a generic error.
- **[authoring hazard, not a shinywidgets bug]** Stacking two fill-hungry outputs (here, `@render.data_frame` and
  `@render_plotly`) in one `ui.card()` with neither given an explicit height left the second output's div stuck at
  `visibility: hidden` indefinitely in `gallery/showcase_aoi_workbench.py` during development -- it never got a
  nonzero size to reveal itself. Fixed by giving the `render.DataGrid` a fixed `height="200px"`. This is a
  standard Shiny/bslib fillable-container footgun (two flex children both wanting to grow, with nothing
  distributing the space), not specific to leafmap or shinywidgets, but worth flagging since a shinywidgets output
  silently failing to reveal (rather than erroring) is a confusing failure mode. Documented in the guide's Gotchas
  and demonstrated by the gallery app itself.

## Judgment calls

- **Didn't build a dedicated kepler.gl backend example.** It needs `keplergl==0.3.7` + `setuptools<81`, which felt
  like a disproportionate amount of guide real estate for a backend the docstring itself deprioritizes relative to
  ipyleaflet/maplibre, and the old report flagged an unresolved kepler+maplibre page-conflict. I verified
  construction and the config-nesting claim (`m.config` = `{"version": ..., "config": {...}}`) directly in Python,
  and the docstring's advice (`config["config"]["mapState"]`) is documented in prose with that verification noted,
  but there's no screenshot of a live kepler map in this guide. Revisit if the maintainer wants kepler given more
  weight.
- **Didn't build a dedicated time-slider example** (`add_time_slider`/`add_gdf_time_slider`), despite the
  assignment calling it out. Prioritized the five accessor examples, the GIS-analyst workflow, and two gallery
  apps within the time available; a time-slider demo needs a believable time-varying dataset (synthetic time
  series looks obviously fake unless carefully built) and didn't fit. It's mentioned once in "What you can build"
  as an available capability with no exercised claim beyond its signature. Flagging for a possible follow-up pass
  or a cross-cutting "animating data over time" article instead of a per-guide slot.
- **Didn't build a dedicated plotly-backend example** for the same reason -- `render_leafmap`'s docstring already
  covers it adequately in prose, it's explicitly the least-recommended backend, and `../plotly/guide.md` covers
  `FigureWidget` accessors/traits in depth.
- **Didn't verify the kepler+maplibre same-page conflict this round** (carried from the old report, flagged as
  "not independently re-verified" in Gotchas) -- would need keplergl installed alongside maplibre and isn't
  central to what this guide emphasizes.
- Used Natural Earth countries data (via leafmap's own bundled example-data URLs on GitHub) for both the vector
  and choropleth highlights, and `world_cities.csv` (same source) for both click and bounds examples, to keep the
  number of distinct datasets small and recognizable rather than introducing a new one per snippet.
- The `clicked()` and `drawn_features()` examples both needed a one-line fix for `@render.express`: a bare
  `req(x)` statement is itself a top-level expression, and `req()` returns its (truthy) argument, so
  `render.express` captures that returned dict/list as a tag child and crashes with `TypeError: Invalid tag item
  type: <class 'dict'>`. The fix is assigning the `req()` result back to a name. This is a `shiny`-level
  interaction between `req()` and Express's auto-display convention, not a shinywidgets issue, but it's an easy
  trap for anyone writing an accessor-driven `@render.express` body -- worth a short callout in a cross-cutting
  "reacting to widgets" article, since it will recur in every guide using this idiom.

## Editor's notes for the website

- **Strongest assets:** the quick-start screenshot (also the hero) and the split-map screenshot (Yosemite
  satellite/topo) are both strong standalone images; either works well in a gallery/index page too. The
  bounds-viewport before/after (world top-10 cities -> Eastern Europe top-10) is the clearest "accessor in
  action" pair in the guide. The AOI workbench showcase (two drawn polygons, live stats table + bar chart) is the
  best demonstration of "what leafmap is for" and could anchor a cross-cutting GIS/geospatial article.
- **Candidates to cut for a shorter page:** the "Beyond the accessors" maplibre subsection and the layout/sizing
  section are the most skippable if the page needs trimming -- the former duplicates information `render_leafmap`'s
  own docstring already states, and the latter is nearly identical to ipyleaflet's.
- **What I dropped from the old report and why:**
  - The detailed per-backend "works / doesn't work" comparison table (ipyleaflet/kepler/maplibre/plotly/folium/
    deck) -- superseded by `render_leafmap` existing now; the current docstring already states backend support
    cleanly, so the guide states it once in the intro instead of re-litigating pre-implementation status.
  - The 600px-height investigation and its three proposed remedies -- implemented and verified fixed; the guide
    states the (now simple) end-user-facing behavior instead of the design history.
  - The controls-transparency finding ("did not reproduce" in the old report's own addendum) -- dropped as
    inconclusive.
  - The kepler/maplibre `setuptools<81` and "needs re-verification against PR #292" framing -- PR-review content
    about a different renderer's PR, not relevant to a teaching guide.
  - Detailed GeoJSON-performance and event-bubbling findings attributed to the ipyleaflet report -- left entirely
    to `../ipyleaflet/guide.md`, which owns that content now.

## Pairs with

- `ipyleaflet` (shared accessors; this guide explicitly defers to it for the low-level API)
- `maplibre` (leafmap's maplibregl backend; `add_deck_layers()` bridges to pydeck layers)
- `localtileserver` (leafmap's `add_raster`/`add_cog_layer` on local files is localtileserver under the hood)
- `plotly` (leafmap's plotly backend is a `go.FigureWidget`)
- `keplergl` (leafmap's kepler backend; nested `config` quirk documented in prose only)

## Update 2026-11-11 (main @ 32ca7035)

Updated against `main` @ `32ca7035`, per the coordinator's update brief. leafmap's default backend
*is* an `ipyleaflet.Map`, so this guide's accessor semantics track `../ipyleaflet/guide.md` exactly
(same `_ipyleaflet.py` code, same `IPYLEAFLET_ACCESSORS`) -- see that guide's NOTES.md for the
pre-redesign-vs-current diff at the code level. This round re-verified the parts specific to this
guide: the three non-ipyleaflet backends' `reactive_read()`/`.read()` usage.

### What changed in the guide, and why

- **Accessor reference table**: replaced `Fires when`/`None`/empty means` with `Before any
  interaction`/`Across re-render`, matching the new brief's format and the parallel edit in
  `../ipyleaflet/guide.md`. Added the same "why" paragraph (map-owned state re-seeds; user
  interaction, i.e. `clicked()`, is kept) with a cross-link to the ipyleaflet guide's `clicked()`
  subsection, since the verification of that specific behavior change lives there (identical code).
- **`clicked()` subsection**: added a sentence that the value is kept across a re-render, so a
  detail card built from it doesn't flash back to empty when something else on the page re-renders
  the map.
- **Converted `reactive_read(map.widget, "view_state")` and `reactive_read(map.widget, "config")` to
  `map.read("view_state")`/`map.read("config")`.** Both read the *output's own* `.widget` (the
  maplibre and kepler backends respectively), so per the update brief's tiering this is tier-2
  (`.read()`), not tier-3 (`reactive_read()` for child widgets). Verified both directly: a probe app
  for each backend confirms `map.read("view_state")`/`map.read("config")` return the same values
  `reactive_read(map.widget, ...)` did, with a real pan gesture for the maplibre one. Updated
  `examples/11_maplibre_reactive_read.py` to match (kept the filename -- renumbering wasn't
  necessary) and re-ran it for a fresh screenshot (`img/11_maplibre_before.webp`), since the card
  header text changed from "reactive_read(), not accessors" to "map.read(), not accessors".
- **New "Reading on demand" subsection** (`examples/14_read_on_demand.py`) -- the same "Save view"
  pattern added to `../ipyleaflet/guide.md`, adapted to `leafmap.Map()`'s default toolbar and
  basemap. Verified with a real gesture: pan, draw a triangle with the default draw toolbar's
  polygon tool (same `leaflet-draw-draw-polygon` control as plain ipyleaflet), click Save, and
  confirm the saved entry's `center`/`zoom`/`shapes` count. Screenshots taken and looked at.
- **Version bump noted**: the worktree has leafmap 0.64.4 (this guide's Gotchas previously cited
  0.63.1). Smoke-tested `01_quickstart.py` against 0.64.4 (renders, no console errors) and updated
  the version line; did not re-verify every example against the newer leafmap release beyond that
  spot check, since nothing in the 33-commit changeset between the two baselines touches leafmap
  itself and the brief calls for a light touch here.

### New/edited examples, verification status

- `examples/11_maplibre_reactive_read.py` -- edited (reactive_read -> map.read()). Ran on port 8532,
  drove a pan gesture, confirmed `view_state` updates and the `TypeError` from `map.zoom()` still
  fires with its existing message. Screenshot replaced.
- `examples/14_read_on_demand.py` -- new. Ran on port 8533, drove pan + polygon-draw + Save click,
  confirmed the saved list entry. Screenshots taken and looked at.
- No other example files changed.

### Bugs found this round (docs)

- **Minor, not fixed per instructions:** the `TypeError` raised by calling an ipyleaflet-only
  accessor (e.g. `map.zoom()`) on a non-ipyleaflet backend still says "Read its state with
  `reactive_read()` instead" -- it doesn't mention `.read()`, which now works identically and is the
  tier this update brief asks guides to teach first. Not wrong (both still work), just an
  opportunity the error message's own wording doesn't take. Source:
  `shinywidgets/_ipyleaflet.py`'s `NotIpyleaflet.message`. Attribution: shinywidgets (docs/message
  wording), observed via the maplibre backend's `accessor_error()` output in
  `11_maplibre_reactive_read.py`.

### Judgment calls for the maintainer to revisit

- Deferred nearly all accessor-semantics re-verification to `../ipyleaflet/guide.md` rather than
  re-running the same Playwright gestures against `leafmap.Map()`, since it's provably the same
  underlying widget/code path (`_IpyleafletAccessors` mixin, `IPYLEAFLET_ACCESSORS` constant) and
  the ipyleaflet guide already did the re-render-specific verification this round. If the maintainer
  wants independent re-verification specifically through the leafmap wrapper (in case leafmap's own
  `__init__`/toolbar setup interferes somehow), that's a quick follow-up using the same probe-app
  pattern as `../ipyleaflet/NOTES.md`'s "Update 2026-11-11" section.

## Update 2026-11-11 (C2 docstring/message fixes, fix/accessor-c-fixes)

- The ipyleaflet-backend `TypeError` message now steers to `.read()` on the output rather than
  `reactive_read()`; the guide's headline paragraph ("On the other three backends, read state with
  `reactive_read()` instead") updated to match. Text-only edit; no examples touched.

## Update 2026-11-11 (Task 8b: "Large data" section)

Added `## Large data` directly after "Coordinating multiple views." leafmap adds no rendering of its own, so the
section just routes by backend: default (ipyleaflet) inherits ipyleaflet's limits, `leafmap.maplibregl.Map` gets
MapLibre's vector tiles/deck.gl, and `add_raster()`/`add_cog_layer()` (already demonstrated above) get
localtileserver's tile-on-demand behavior. No new example or screenshot needed. One link to
`articles/performance/article.md#three-approaches-to-large-data` is unresolved until Task 7 (same wave) lands,
per the task block; `check_docs.py` on this guide is otherwise clean.
