# NOTES: GeoViews guide

## Versions / environment

- Date: 2026-11-02.
- Worktree: `main-wt` detached at shinywidgets main (commit `00f90249`, "fix(plotly): bind accessor events when
  Plotly draws after the bind request and display (#392)").
- geoviews 1.16.0, cartopy 0.25.0, holoviews 1.23.2, hvplot 0.12.2, panel 1.10.0, bokeh 3.10.1,
  jupyter_bokeh 4.1.0, geopandas 1.2.0, shapely 2.2.0, pyproj 3.8.0, xyzservices 2026.9.1, shiny 1.9.0,
  datashader 0.19.1 (installed in the shared venv; no `--with` overlays were used -- everything needed was
  already present per `uv pip list`).
- Browser: headless Chromium via Playwright, 1280x800-1100 depending on test, `device_scale_factor=2` for
  screenshots (1x for coordinate-measurement scripts). `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist` launch args throughout (not strictly required for Bokeh's 2D canvas, used
  defensively per the brief).

## Verification table

| file | ran | screenshot | gesture driven | notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a | OSM tiles loaded and painted |
| `examples/02_choropleth.py` | yes | yes | n/a | explicit vs. hvPlot shortcut render identically |
| `examples/03_projections.py` | yes | yes | n/a | confirms tiles disappear under non-Mercator projection |
| `examples/04_tap_detail.py` | yes | yes (before/after) | click | detail card updated with nearest station |
| `examples/05_boundsxy_table.py` | yes | yes (before/after) | box-select drag | table filtered 249 -> 46 rows |
| `examples/06_rangexy_viewport.py` | yes | yes (before/after) | scroll-zoom | value boxes 249 -> 177 stations, no render loop (log checked) |
| `examples/07_inplace_filter.py` | yes | yes (before/after) | scroll-zoom + slider drag | zoom preserved exactly across the filter |
| `examples/08_rasterize_scale.py` | yes | yes | n/a (static comparison) | raw vs. rasterized render, no gesture needed |
| `gallery/template_city_map.py` | yes | yes (before/after) | click | detail card -> "Tokyo, 14.0M people" |
| `gallery/showcase_quake_explorer.py` | yes | yes (initial/selected) | box-select + click | value boxes, table, and detail card all confirmed via DOM text, not just visually |

No reactive accessors exist on `render_holoviews` (confirmed: no `_HoloviewsAccessors`-style mixin in
`_render_widget.py`), so there's nothing to drive the "every accessor exercised in a browser" requirement --
every interactive example above instead verifies the stream-subscriber recipe with a real gesture and reads the
result back from a Shiny output's DOM text (`page.locator(...).inner_text()`), not just a screenshot.

## Bugs found

### Retracted: "BoundsXY silently fails on a narrow responsive canvas"

**Originally reported** [sw/up, worth a second opinion, possibly release-relevant]: a `hv.streams.BoundsXY`
(box-select) subscriber never fires when its plot's responsive canvas renders below roughly 500-650px wide, with
`Tap` on the identical element unaffected at any width -- isolated by varying viewport width against a fixed
fractional drag gesture (fires at ~1062px and ~642px canvases, never fires at ~462px), reproduced with and without
tiles and with plain `hv.Points`/no geoviews at all, and directly responsible for a showcase gallery bug during
development (box-select silently doing nothing with the map in a `layout_columns()` column next to a detail card).

**Retracted** following `../investigations/narrow-canvas-and-subclass/INVESTIGATION.md` (Item A, which
independently re-tested this exact claim, including the "plain `hv.Points`, no geoviews" case). Root cause:
Bokeh's `BoxSelectTool` only starts a selection when the mousedown lands inside the plot's *data frame* (confirmed
via `view.frame.bbox.left`), not its fixed-pixel (~49px) y-axis label margin. A drag computed as a fraction of the
canvas's full bounding rect -- the natural way to drive a resizable plot, and the method my own isolation script
used -- clears that fixed margin comfortably on a wide canvas (a few percent of its width) but lands *inside* the
margin once the canvas is narrow enough that the same 49px becomes ten-plus percent of its width. Confirmed down
to a 222px-wide canvas: a drag computed from the plot's actual `frame.bbox` (not the full canvas rect) selects
correctly at every width tested. This is a property of how a synthetic test drag is computed, not a real
shinywidgets/holoviews/Bokeh defect and not width-dependent in any way a real user would hit -- a person dragging
with a mouse naturally starts inside the visible plot area.

No code or layout change is needed. `gallery/showcase_quake_explorer.py` and `examples/05_boundsxy_table.py` keep
their full-width map layout as a plain UX preference now, not a workaround; the guide's Gotchas entry and the
showcase's code comment have been corrected accordingly.

### Carried forward from the HoloViews guide (not re-litigated in depth here)

- No reactive accessors on `render_holoviews` -- by design, not a bug.
- `RangeXY`'s loop is real but has a precise, documented, avoidable trigger (idempotent subscriber value) -- see
  `../holoviews/INVESTIGATION.md` and this guide's own verification (`examples/06_rangexy_viewport.py`, checked
  the server log for the `BokehModel was closed` signature after load and after a multi-step scroll-zoom; none
  appeared).
- `ui.sidebar()` / second-output `link_selections` claims: retracted upstream (not applicable here anyway --
  this guide never uses `link_selections`).
- Streams must be attached to a `DynamicMap`, not re-created inside its callback -- this is implied by the
  HoloViews guide's streams section but I hit it concretely here (see "Judgment calls" below) and call it out
  explicitly in this guide's prose since the failure mode (silent, no error) is easy to reproduce by accident.

### Upstream (geoviews/cartopy/tiles), re-verified or newly checked today

- geoviews 1.15/1.16 + cartopy 0.26 incompatibility (`KeyError: 'lon_0'`): the `cartopy<0.26` pin in
  `pyproject.toml` is still necessary with the versions installed today (geoviews 1.16.0, which is newer than the
  1.15.1 the old report tested, cartopy 0.25.0). Not independently re-reproduced against cartopy 0.26 this pass
  (would require an overlay, avoided per the disk-space/machine-load constraints); carried forward from the old
  report and the pin comment in `pyproject.toml`, both of which agree it's still needed.
- `CartoLight`/`CartoDark` need an API key now (confirmed via the Esri/OSM-only approach throughout; not
  independently re-curled today, carried forward from the old report, which is corroborated by `xyzservices`
  2026.9.1 being installed, a version well past when CARTO's free tier changed).
- Non-Mercator `projection=` drops tiles silently: reproduced today (`examples/03_projections.py`).
- `.opts()` mutates `gv.tile_sources.*`/`gv.feature.*` singletons in place: not independently re-reproduced this
  pass (no example needed it), carried forward from the old report as a documented gotcha since the mechanism
  (plain Python object identity) hasn't changed.
- `gv.feature.*` downloads Natural Earth data synchronously on first use: reproduced today as a side effect of
  `examples/03_projections.py` (saw the `cartopy.io` `DownloadWarning` in the server log on first run).

### Not re-chased this pass (carried forward from the old report without independent re-verification)

- `hover_tooltips=` resetting after a `DynamicMap` update (old report 3.6) -- not hit in this guide's examples
  (none use `hover_tooltips=`; all use `tools=[...]`/`hover` directly).
- `xlim`/`ylim` as Web Mercator meters when tiles are present (old report 3.5) -- re-confirmed conceptually (see
  the coordinate-space Gotcha above) but not re-measured with the exact `lon_lat_to_easting_northing` numbers.

## Judgment calls

- **No `shinywidgets[geoviews]` extra exists** in `pyproject.toml` -- only `holoviews` (`holoviews`, `panel`,
  `jupyter_bokeh>=4.1`). geoviews/cartopy only appear in the internal `test` dependency group. I wrote the
  Installation section to tell users to install `shinywidgets[holoviews]` plus `geoviews` and `cartopy<0.26`
  directly, mirroring how the HoloViews guide already tells users to add `hvplot` on top of the same extra. This
  matches `AS_WIDGET_MAP`'s dispatch (geoviews objects already route through `as_widget_holoviews`, no code
  change needed), so no extra is strictly required for correctness -- but the maintainer may want a dedicated
  `shinywidgets[geoviews]` extra (`holoviews` + `geoviews` + the `cartopy<0.26` pin) for discoverability, same as
  every other per-library extra in the roster. Flagging for a second opinion rather than assuming either way.
- Synthetic earthquake dataset (`examples/07_inplace_filter.py`, `gallery/showcase_quake_explorer.py`): real point
  count is 6,080 (19 interpolated segments x 320 points), labeled "6,000" in titles/comments as a round,
  human-friendly approximation. Called out here in case the maintainer prefers either the exact number or a
  code change to hit exactly 6,000.
- Used `px.data.carshare()` (Montreal car-share stations) for four of the eight examples (quickstart, Tap,
  BoundsXY, RangeXY) since it's a small, real, recognizable lon/lat dataset with a numeric column to color/size
  by. The ipyleaflet guide's showcase also uses this dataset (`showcase_carshare_explorer.py`) -- flagging the
  overlap rather than hiding it; I judged a shared, well-known real dataset was preferable to inventing a new one
  purely for novelty, especially since the two guides use it for entirely different interaction mechanics
  (ipyleaflet's draw tool vs. this guide's stream-subscriber recipe).
- `examples/03_projections.py`'s synthetic scatter (300 uniform random lon/lat points) is there purely to make
  the projection distortion and the tile-disappearing effect visually obvious everywhere on the globe at once;
  a real dataset would cluster and make the Robinson-vs-Mercator comparison harder to see at a glance.

## Editor's notes for the website

- Strongest sections: the projections before/after (`03_projections.webp`) makes the "tiles are Mercator-only"
  point immediately obvious without reading any text; the in-place-filter before/after
  (`07_inplace_before/after.webp`) is a clean, visually striking zoom-preservation demo; the showcase gallery app
  screenshots show all three interaction patterns landing in one dashboard with real, changed numbers in the
  value boxes.
- Could cut for a shorter page: the "Paths" subsection (deliberately thin -- there's nothing geography-specific
  to show beyond what Points/Polygons already demonstrate) and the rasterize/performance section's code listing
  (could become just the screenshot + two sentences, since the real teaching content is in the linked
  Datashader/HoloViews guides).
- The coordinate-space explanation (streams report lon/lat even under Mercator tiles, for all three stream types)
  is the single most useful, least obvious fact in this guide -- I'd keep that prominent even in a trimmed
  version.

## What was dropped from the old report and why

- The shiny-1.6-vs-1.9 stream-latency finding (old report 3.1): shinywidgets now requires `shiny>=1.9.0`
  (`pyproject.toml` `dependencies`), so the flush-ordering workaround (`flush_soon()`) no longer applies and would
  be actively misleading to carry forward.
- The `output_widget(height=)` fixed-height collapse (old report 3.2): fixed on main per the HoloViews guide's own
  verification; not re-litigated here, just referenced via the shared Layout and sizing section.
- The first-box-select-after-same-flush-Pipe-send bug (old report 3.3, never fully attributed): not reproduced or
  investigated this pass; none of this guide's examples send `Pipe` data in the same flush as the initial render
  (the in-place filter example's effect fires on a `min_mag` dependency, not an unconditional startup write, and
  the Pipe is seeded with the full dataset at construction time).
- The `hover_tooltips=` reset and Mercator-meters `xlim` findings: kept as brief Gotchas bullets (not full
  write-ups) since neither was exercised by this guide's examples; see "Not re-chased this pass" above.
- CartoDB/CARTO tiles needing an API key, cartopy 0.26 incompatibility, feature-download-on-first-use: kept,
  since they reproduce today and are the most likely things a new user actually hits.

## Pairs with (for cross-widget articles)

- **holoviews**: this guide is explicitly a thin layer on top of it; nearly every recipe links back.
- **datashader**: the rasterize=True handoff (`examples/08_rasterize_scale.py`).
- **lonboard**: performance/scale handoff recommendation (GPU point-picking at higher point counts).
- **ipyleaflet** / **leafmap**: "choose this vs." comparison in the intro (Leaflet-style API, drawing tools).
- **maplibre**: "choose this vs." comparison (vector tiles, Mapbox GL style spec).

## Update 2026-11-11 (main @ 32ca7035)

- shinywidgets commit: `main` @ `32ca7035` (worktree `main-wt`). Same library versions as the prior pass (geoviews
  1.16.0, holoviews 1.23.2, hvplot 0.12.2, cartopy 0.25.0, panel 1.10.0, bokeh 3.10.1, geopandas 1.2.0,
  jupyter_bokeh 4.1.0), Python 3.13.17.
- **Fixed stale `RangeXY`-loop framing (3 spots) left over from before the HoloViews guide's own correction.**
  This guide's "What you can build" pattern-3 summary, its code comment in `examples/06_rangexy_viewport.py`'s
  inline docstring, the "Rate limiting" paragraph, and two Gotchas entries all still described the old,
  since-fixed mechanism ("`RangeXY` was flagged there as broken", "a naive subscriber causes a render loop") as
  if it were still a live risk requiring a specific workaround, rather than crediting the shinywidgets-side fix
  (#411, `reactive.isolate()` around widget coercion) that the HoloViews guide's own Gotchas section already
  documents correctly. Rewrote all five to point at the HoloViews guide's Gotchas for the mechanism, and to frame
  "store the range tuple, not a counter" as what it now actually is: good practice to avoid wasted invalidation,
  not a crash-avoidance requirement. Also fixed a factually wrong claim that this guide's viewport pattern "isn't
  in the HoloViews guide" -- it is now (`examples/10_zoom_range_summary.py` there), added during that guide's own
  correction pass; this guide's version differs only in the lon/lat coordinate-space detail.
- **Re-verified the fix directly against this guide's own example**, not just the shared HoloViews repro:
  ran `examples/06_rangexy_viewport.py` with a real `page.mouse.wheel()` scroll-zoom (8 steps). Result:
  "Stations visible" went 249 -> 115 (the viewport accessor genuinely updates), **zero**
  `RuntimeError: BokehModel was closed` lines in the server log. No code in this file changed -- this re-confirms
  an existing, already-correct claim in the guide text, now with an accurate explanation attached to it.
- Added a one-line mention of `.read("trait")` (the new `#437` generic reader) alongside `reactive_read(x.widget,
  "trait")` in "Beyond streams: `reactive_read`", with the same "neither is useful here" conclusion as before
  (`render_holoviews` has no accessors, and a `BokehModel`'s own traits aren't map-specific).
- **Confirmed `param(name)` does not reach `render_holoviews`** (same check as the HoloViews and Datashader
  guides): no `param()` method and no `_dynamic_accessor_spec()` override on the class in
  `shinywidgets/_render_widget.py`. Not mentioned in this guide and nothing needed adding.
- No other PR in 00f90249..32ca7035 touches anything this guide documents (checked `shinywidgets/_as_widget.py`'s
  `as_widget_holoviews()` and the `render_holoviews` class directly -- unchanged beyond what's already covered by
  the HoloViews guide's own update notes).

### Bugs found (2026-11-11)

None newly found; no previously-reported items in this guide were affected by anything in 00f90249..32ca7035.

## Scratch cleanup

All throwaway probe apps, debug scripts, and mid-drag screenshots used to isolate the BoundsXY-narrow-canvas bug
were deleted from the scratch directory after use; nothing was left there beyond the `run.sh`/`stop.sh` helpers
and server logs.

## Update 2026-11-11 (Task 8b: "Large data" section)

Added `## Large data` directly after "Coordinating multiple views." Reuses the existing
"Scaling up: rasterizing points" subsection and its 200,000-point raw-vs-rasterized measurement rather than
re-measuring or duplicating it; the new section is a short pointer plus the three-approaches framing. No new
example or screenshot. One link to `articles/performance/article.md#three-approaches-to-large-data` is
unresolved until Task 7 (same wave) lands, per the task block. `check_docs.py --links` on this guide shows only
that one expected unresolved anchor; `--snippets` is unchanged from `BASELINE.txt` (the one pre-existing
`unlinked snippet` at line 464, not touched by this edit).
