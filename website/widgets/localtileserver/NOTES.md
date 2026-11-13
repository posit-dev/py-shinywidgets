# NOTES: localtileserver guide

## Versions

- localtileserver 1.0.0 (pinned in examples: `get_leaflet_tile_layer()` only sets `tile_server`
  unconditionally since 1.0.0), rasterio 1.5.2, rio-tiler 9.4.13, leafmap 0.64.0 (installed but unused in the
  final guide body; `leafmap`'s own `add_raster()` is covered by the leafmap guide, which links here).
- shinywidgets @ `origin/main` (worktree), shiny 1.9.0, ipyleaflet 0.20.0, plotly 6.9.0 (already in the base
  venv, no overlay needed).
- Date: 2026-11-02. All overlays via `uv run --no-sync --with 'localtileserver>=1.0.0' python -m shiny run ...`
  (the `shiny` console script's shebang bypasses `--with`, per BRIEF.md).

## Verification table

| File | Ran? | Screenshot? | Gesture driven? | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes (hero + quickstart) | n/a (static) | network requests confirmed tiles via `/proxy/{port}/...sw_token=...` |
| `examples/02_restyle.py` | yes | before/after | yes (select band/colormap, drag both range slider handles via Playwright mouse) | render counter confirmed 1 render across all changes |
| `examples/03_click_sample.py` | yes | before/after | yes (Playwright click on map) | `client.point()` value (3661 m) plausible vs. nearby labeled peaks |
| `examples/04_draw_zonal_stats.py` | yes | before/after | yes (Playwright click-drag rectangle via DrawControl) | histogram populated with plausible bimodal (water/land) shape |
| `gallery/template_raster_viewer.py` | yes | yes | yes (colormap select + click) | |
| `gallery/showcase_raster_explorer.py` | yes | yes | yes (click + draw + colormap select, in one pass) | first version (remote CO-elevation DEM, `client.feature()` over a larger extent) intermittently stalled under heavy machine load; switched showcase to the bundled Bahamas sample for reliability -- see "Judgment calls" |
| security guard (403) | yes | n/a (curl evidence) | n/a | verified against a live app's mounted proxy: legit token 200; same filename without token 403; `/etc/passwd` 403; SSRF-style `url=` to the STAC endpoint 403 |
| path-prefix deployment | yes | yes (network capture) | n/a | Shiny App ASGI-mounted under `/app1/` via a Starlette `Mount` wrapper; tile requests resolved to `.../app1/proxy/{port}/...` |

No accessors to verify -- localtileserver has none of its own; all interaction comes from ipyleaflet's
`clicked()`/`drawn_features()`/`bounds()`/`zoom()`/`center()`, already verified in the ipyleaflet guide.

## Bugs found

- **[up, gotcha not a bug] `TileClient.part(bbox)`'s `bounds_crs` defaults to the dataset's native CRS**, not
  WGS84, even though `bounds()`/`center()` return WGS84 by default. Passing a WGS84 bbox (e.g. from a drawn
  rectangle) without `bounds_crs="EPSG:4326"` silently returns a near-1x1-pixel crop rather than raising.
  Verified against the bundled Bahamas sample (native CRS EPSG:32618/UTM 18N): the no-`bounds_crs` call and the
  explicit `bounds_crs="EPSG:4326"` call differ dramatically in output size. `client.feature()` (GeoJSON input)
  has no such problem -- it's WGS84 by spec and localtileserver reprojects internally -- which is why the guide
  teaches `feature()`, not `part()`, for the draw-rectangle pattern. Docstring is technically accurate; worth a
  one-line clarification upstream (e.g. "unlike `bounds()`, defaults to the dataset's native CRS").
- **[docs, minor] `client.point(...).array` holds NumPy scalar types** (`np.uint8`, etc.), which under NumPy
  2.x's new repr show as `np.uint8(19)` when put in a list/f-string without a format spec. Not a bug, just a
  display trap; noted in Gotchas.
- No shinywidgets bugs found. The loopback-proxy feature (PR #378) is new, heavily reviewed (5 rounds per the
  design doc), and every claim in this guide was independently re-verified rather than taken on faith:
  auto-wiring, relative-URL path-prefix behavior, the capability-token guard (legit/no-token/arbitrary-path/SSRF
  cases), and in-place restyle (render-counter proof).
- Carried from the old evaluation report, not re-verified for this guide: invalid lowercase rio-tiler colormap
  names raise inside the restyling effect and crash the session (noted in Gotchas, attributed as carried-over).

## Judgment calls

- **Gallery showcase switched from a remote DEM to the bundled local Bahamas sample.** The coordinator's
  terminal crashed mid-session under a system-wide load spike (200+) with disk pressure; a resume message asked
  for lean verification (one server/browser at a time, no new overlays beyond `--with localtileserver`, avoid
  large/slow network calls). The first showcase draft used `examples.get_co_elevation()` (a remote `/vsicurl/`
  COG) and a `client.feature()` call over a user-drawn ~1000 ha extent; a verification pass hung past the
  available wait time (ambiguous whether it was genuinely slow under the system load spike, or just needed a
  longer timeout -- not conclusively root-caused). Rather than debug a slow/flaky network path under constrained
  conditions, the showcase was rewritten around the bundled local Bahamas raster (same `client.feature()` API,
  no network, demonstrably fast and reliable in two clean re-runs). The public-COG network path is still
  covered honestly elsewhere (quick, single-pixel `client.point()` calls in `03_click_sample.py`, and the
  restyle example's larger SF Bay COG) with an explicit "needs network, first open takes a few seconds" callout
  in the guide's "Using real data" section. Worth a second opinion: is the remote-DEM zonal-stats path worth a
  follow-up verification pass once the machine is calm, to confirm it wasn't a real bug?
- **No `render_leafmap` example in this guide's body.** leafmap's `add_raster()` already has a full worked
  example with its own gotchas in the leafmap guide, which links here for the deployment/security mechanism;
  duplicating it seemed like exactly the "don't regurgitate" case the brief warns against. This guide instead
  covers the lower-level `TileClient` + `get_leaflet_tile_layer()` API both paths share.
- **Path-prefix verification used a throwaway Starlette-`Mount` wrapper script**, not a shipped example (it's
  deployment-infrastructure simulation, not teaching material a reader would copy). Kept in scratch per
  BRIEF.md's "throwaway probe apps ... go in scratch, not in the guide dir." The guide reports the method and
  result in prose rather than as a runnable code block, so as not to imply it's a snippet to copy.
- **`accessors: []` in the frontmatter** -- localtileserver has none of its own; all interaction in this guide
  comes from the host renderer's accessors (ipyleaflet's, documented in that guide). Flagging in case the
  website template expects a non-empty list.

## Editor's notes for the website

- Strongest material: the security-guard curl evidence and the path-prefix verification -- this is the one
  guide in the roster where "it deploys safely" is the actual headline feature, not a footnote, so lead with it
  if space is tight.
- The restyle before/after pair (San Francisco COG, true-color -> magma-on-red-band) is the most visually
  striking screenshot; good hero/thumbnail candidate alongside the Bahamas quickstart.
- Could cut for a shorter page: the "Using real data" section's list of other `localtileserver.examples`
  functions (`get_elevation()` etc.) -- useful for a reader experimenting locally, skippable for the web page.
- What was dropped from the old `docs/widget-reports/localtileserver/report.md`: the jupyter-loopback
  CommBridge fallback (3.6) -- now dead weight since the proxy is automatic and strictly better (same-origin,
  HTTP-cached, doesn't tax the Shiny websocket); the manual 3-line mount recipe (now automatic); the
  bytes/perf comparison table (direct vs proxy vs bridge) -- superseded by "it just works," not worth
  re-litigating; `client.bounds()` returning `(south, north, west, east)` rather than rasterio's
  `(west, south, east, north)` -- true but not hit by any pattern in this guide (everything here uses
  `client.center()` or GeoJSON, which sidestep it); folium (no widget hook, stays a manual recipe, out of scope
  for a widget-integration guide).

## Update 2026-11-11 (main @ 32ca7035)

Light-touch pass per the coordinator's update brief: localtileserver declares no accessors of its
own (`accessors: []`), and this guide's text never stated the old event/state taxonomy or any
"resets on re-render" claim for the ipyleaflet accessors it uses (`clicked()`, `drawn_features()`,
`bounds()`, `zoom()`, `center()`) -- it already deferred entirely to `../ipyleaflet/guide.md` for
their semantics, which that guide now documents correctly for current `main`. **No `guide.md`
content changes were needed.**

### What was checked

- Smoke-tested all four `examples/*.py` against `main` @ `32ca7035` (worktree venv, localtileserver
  overlaid via `uv run --no-sync --with 'localtileserver>=1.0.0' ...`, not already in the venv):
  - `01_quickstart.py`: boots, map renders, no console errors.
  - `02_restyle.py`: drove a real gesture (select band, select colormap) with Playwright; the
    render counter stayed at 1 across both changes, confirming "restyling never re-renders" still
    holds on current `main`.
  - `03_click_sample.py`: drove a real click with Playwright; `clicked()` fired and
    `client.point()` returned a plausible elevation (3442 m) for the clicked coordinate.
  - `04_draw_zonal_stats.py`: drove a real rectangle draw (DrawControl) with Playwright;
    `drawn_features()` fired and the histogram populated with the expected shape. Not re-saved as a
    new screenshot since the result is consistent with the existing one (no narrative change to
    justify replacing it).
- No `reactive_read(x.widget, ...)` calls exist in this guide to convert to `.read()` -- it reads
  ipyleaflet's named accessors directly (`map.clicked()`, `map.drawn_features()`, etc.), which is
  already the correct (tier-1) usage.
- Checked localtileserver's installed version in the worktree: not pinned/present by default
  (needs the `--with` overlay, confirmed via `uv pip list` showing no `localtileserver` row before
  installing it). The overlay installed whatever's current on PyPI; didn't pin to exactly 1.0.0 for
  this smoke pass since no version-sensitive behavior was in question (only "does it still render
  and respond to gestures").

### Bugs found this round

None. All four examples still work exactly as documented.

## Update 2026-11-11 (Task 8b: "Large data" section)

Added `## Large data`. **Deviation from the task block:** this guide has no "Coordinating multiple views"
heading (its structure is Installation / Quick start / What you can build / Reacting to user interaction /
Updating the widget from Python / Behind the scenes: the deployment story / Using real data / Gotchas and
limitations / Gallery candidates / Learn more), so the literal instruction ("insert directly after Coordinating
multiple views") doesn't apply. Inserted the section after "Using real data" and before "Gotchas and
limitations" instead -- the closest analogous spot (last content section before the wrap-up material), and the
one place the guide hadn't already made the point implicitly. The section itself restates, in the section
contract's shape, what "Behind the scenes" and "Using real data" already demonstrate (tile-on-demand, COG
overviews) rather than re-measuring; no new example or screenshot. One link to
`articles/performance/article.md#three-approaches-to-large-data` is unresolved until Task 7 (same wave) lands,
per the task block; `check_docs.py` on this guide is otherwise clean.
