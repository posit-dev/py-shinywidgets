# NOTES: ipyleaflet guide

## Versions / environment

- Date: 2026-10-30.
- shinywidgets: verified against a detached worktree snapshot pinned at commit `38a1796b`
  (main @ 38a1796b1a18095f18d10b4f137d72af2a9d416d, "test(ipycanvas): click via the locator, not a
  pre-measured bounding box (#391)"), created specifically because the shared main checkout was mutated by other
  concurrent agents mid-task (see "Operating notes" below). `shinywidgets/_ipyleaflet.py` and the
  `_IpyleafletAccessors` mixin in `_render_widget.py` are unchanged since commit `fa28de39` (2026-10-29,
  "feat: reactive accessors for quak, mosaic, perspective, lonboard, ipyleaflet, leafmap (#384)").
- ipyleaflet 0.20.0, shiny 1.9.0, plotly 6.9.0, pandas 3.1.0, geopandas 1.2.0, shapely 2.2.0, branca 0.8.2.
- Browser: headless Chromium via Playwright, 1280x800, `device_scale_factor=2`. No WebGL/swiftshader flags
  needed -- ipyleaflet is DOM-based and rendered correctly in default headless mode.

## Verification table

| file | ran | screenshot | gesture driven | accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | marker click (popup) | n/a |
| `examples/02_basemaps.py` | yes | yes (3) | LayersControl radio clicks | n/a |
| `examples/03_markers_clusters.py` | yes | yes | n/a | n/a |
| `examples/04_choropleth.py` | yes | yes | n/a | n/a |
| `examples/05_draw_tool.py` | yes | yes (before/after) | drew a triangle (click x2 + dblclick) | `drawn_features()` yes |
| `examples/06_camera_state.py` | yes | yes (before/after) | zoom-in control click | `bounds()`, `zoom()`, `center()` yes |
| `examples/07_clicked.py` | yes | yes (before/after) | map click + dblclick | `clicked()` yes |
| `examples/08_reactive_read_marker_drag.py` | yes | yes (before/after) | marker drag | `reactive_read` yes |
| `examples/09_rate_limiting.py` | yes | yes | 30-step marker drag | throttle behavior yes (30 mousemoves -> 2 effect runs) |
| `examples/10_inplace_updates.py` | yes | yes (4 states) | checkbox/radio toggles | n/a (in-place update) |
| `examples/11_linked_spatial_filter.py` | yes | yes (before/after) | drew a rectangle | `drawn_features()` yes (201/249 rows) |
| `examples/12_linked_viewport_summary.py` | yes | yes (before/after) | 2x zoom-in | `bounds()` yes (249 -> 172 visible) |
| `examples/13_linked_click_nearest.py` | yes | yes (before/after) | map click | `clicked()` yes |
| `examples/14_linked_two_maps.py` | yes | yes (before/after) | drag on main map | `center()`, `bounds()` yes |
| `examples/15_split_map.py` | yes | yes | n/a (static comparison) | n/a |
| `gallery/template_spatial_explorer.py` | yes | yes (before/after) | map click | `bounds()`, `clicked()` yes |
| `gallery/showcase_carshare_explorer.py` | yes | yes (before/after) | drew a triangle + basemap toggle | `drawn_features()`, `bounds()` yes |

**Accessor coverage, each with a real browser gesture:**
- `bounds()`: yes (06, 12, template)
- `zoom()`: yes (06, via zoom-in control + Python-side slider set)
- `center()`: yes (06, 14)
- `clicked()`: yes (07, 13, template) -- including a dblclick gesture to check the "fires two clicks" docstring
  claim (see Bugs found)
- `drawn_features()`: yes (05, 11, showcase) -- draw, and (via `tests/unit/test_ipyleaflet_accessors.py`, not
  re-driven in a browser for this guide) the `TypeError` path when no `DrawControl` is present

## Bugs found

### shinywidgets / library behavior (verified on current `main`)

None found in shinywidgets' own accessor implementation -- `shinywidgets/_ipyleaflet.py` and the
`_IpyleafletAccessors` mixin behaved exactly as documented in every browser test above, including the subtler
contracts (`bounds()` canceling until first report, `drawn_features()` raising without a `DrawControl`, the
`NotIpyleaflet` guard, event-vs-state reset semantics). The unit suite
(`tests/unit/test_ipyleaflet_accessors.py`, 11 tests) also passed unmodified against the snapshot used here.

### Upstream (ipyleaflet) quirks found while building examples

1. **Multiple `base=True` tile layers all render simultaneously until the user interacts with `LayersControl`.**
   Reproducible: add two or three `base=True` `TileLayer`s and a `LayersControl`, load the page without clicking
   anything. All layers stay `visible=True`; Leaflet just stacks them, so whichever was added *last* ends up on
   top and is what the user actually sees -- even though the control's radio button shows the *first* one
   selected. This is a real, confirmed-today mismatch between "what the control says is active" and "what's
   rendered." Fix used in the guide: re-add your intended default layer last (3 extra lines). Not previously
   documented in the old `docs/widget-reports/ipyleaflet/report.md`. Judgment call: I treated this as an
   ipyleaflet/jupyter-leaflet behavior (not shinywidgets'), since it reproduces with plain `Map.add()` calls and
   no shinywidgets-specific code in the loop -- worth a second opinion, since I did not test it against a plain
   Jupyter notebook to fully rule out shinywidgets' render pipeline.
2. **`rectangle={}` / `circle={}` on `DrawControl` silently disables the tool**, even though `{}` is also the
   trait's own default and looks like "accepted, empty options" rather than "off." The other three tools
   (`polygon`, `polyline`, `circlemarker`) default to `{"shapeOptions": {}}` (one key) and are enabled. Passing
   `{"shapeOptions": {}}` for rectangle/circle turns them on. This cost real debugging time while writing
   `examples/11_linked_spatial_filter.py` (rectangle tool silently missing from the toolbar).
3. **`basemap_to_tiles()` does not set `.base = True`** on the tile layer it returns. Code that looks up "the
   current base layer" via `next(lyr for lyr in m.layers if lyr.base)` will raise `StopIteration` on the second
   swap if the first replacement's `.base` was never set. This was already called out in the old report
   (§6 "Gotchas") and still reproduces; carried forward.

### Docstring correction (not a behavior bug, but the docstring's framing is misleading)

`clicked()`'s docstring says "A double-click fires two clicks (the `dblclick` itself is ignored)." That's true of
the raw browser events ipyleaflet's `on_interaction` reports. But `clicked()` is an **event-kind accessor with
the library's default `priority="input"`** (it doesn't opt into `priority="event"`), so `payloads_equal()`
deduplicates a raw value identical to the previous one -- and the two clicks of a double-click land on the exact
same `(lat, lng)`, so the second one never republishes. Verified directly: a counter effect on `clicked()` showed
exactly **1** increment after one `dblclick()` gesture, not 2. This may be intentional (nobody has asked for
double-click detection via `clicked()`), but the docstring as written would lead a reader to expect two
observable updates. Flagged in the guide's `clicked()` section and in Gotchas; recommend either rewording the
docstring to clarify "two browser events, but input-priority dedup usually collapses them to one," or giving
`CLICKED` `priority="event"` if double-click detection is meant to be supported. I did not change the code.

## Judgment calls for the maintainer

- **Dataset swap mid-task:** the coordinator's amendment asked for real/recognizable datasets over synthetic
  ones where possible. I switched every multi-point example (03, 04, 11, 12, 13, both gallery apps) from a
  synthetic "NYC coffee shops" dataset (used by the old report and my first draft) to `plotly.express.data.
  carshare()` -- 249 real, anonymized car2go pod locations and usage hours around Montreal, bundled with plotly
  (already a dependency), no network needed. This meant retheming the showcase gallery app from "coffee crawl" to
  "car-share pod explorer." I did not revisit the single-point examples (01, 06, 07, 08, 09, 10, 14), which use a
  real place (Union Square, NYC) or an arbitrary single marker -- those didn't need a "dataset" swap.
- **Gallery/example header style:** per the coordinator's amendment, gallery file headers are `#`-comment blocks,
  not module docstrings (a bare docstring renders as visible page text in Shiny Express). Applied to both
  `gallery/*.py` files.
- **Multi-base-layer "before" screenshot:** `02_basemaps_before.webp` is taken after a 1.5 s settle so all three
  tile providers finish loading before the shot (otherwise it shows a transient loading jigsaw as different
  providers' tiles arrive at different speeds, which is not a bug, just a slow screenshot timing artifact
  separate from item 1 above).
- **`clicked()` double-click wording:** see "Docstring correction" above -- I wrote the guide copy and the
  Gotcha entry to explain the actual observed behavior rather than only repeating the docstring; a second
  opinion on whether to also update the docstring/code would be welcome.
- **Scope of `reactive_read()` coverage:** I showed one `reactive_read()` example (draggable marker `location`)
  rather than enumerating every possible layer trait, per the brief's "show the escape hatch" guidance. GeoJSON
  hover/click callbacks and `DrawControl.last_action`/`last_draw` are mentioned in prose only, not demonstrated.
- **"Marker clicks bubble to the map" and "transparent controls outside JupyterLab"** gotchas are carried over
  from the old report without independent re-verification in this pass (noted as such in the guide text) --
  the first follows directly from Leaflet's event model and seemed low-risk to assert; the second did *not*
  reproduce in any of this guide's ~20 screenshots (every zoom button, draw toolbar, and legend rendered with a
  solid background), so I downgraded it from "confirmed bug" (old report) to "known upstream wart, not currently
  reproducing" pending another agent's check with a different control mix.

## What was dropped from the old report and why

- `docs/widget-reports/ipyleaflet/report.md`'s CSS-selector bug (`output_widget(height="auto")` rendering an
  invisible 0-height map) is **fixed on current `main`** (`shinywidgets/static/shinywidgets.css` now excludes
  `auto`/`fit-content`/`min-content`/`max-content` from the height-override selector) -- dropped as stale.
- The leafmap-600px-default gap is **fixed on current `main`** via `leafmap_layout_defaults()` in
  `_render_widget_base.py` -- out of scope for this guide anyway (leafmap has its own guide).
- The PR-review material (CI status, rebase conflicts, scorecard, "should-fix" numbered list aimed at a draft PR)
  is entirely dropped -- this guide is user-facing documentation, not a PR review, and the PR in question has
  long since merged.
- The localtileserver section is intentionally kept to one short paragraph with a cross-link, per the
  assignment (another agent covers it in depth).
- The #215 "many-widget reload" performance investigation is condensed to one Gotcha bullet ("prefer one GeoJSON
  layer"); the old report's full benchmark table felt like more detail than a teaching guide needs, though the
  qualitative lesson (GeoJSON >> many Markers) is preserved.

## Cross-widget pairings (for the coordinator's cross-cutting articles)

- **pairs with: plotly** -- `examples/12_linked_viewport_summary.py` (map viewport -> `render_plotly` bar chart).
- Candidate not built: a pairing with a table-focused renderer (itables/reactable) showing `drawn_features()` ->
  a sortable/filterable grid instead of `render.data_frame`'s plain `DataGrid`; `11_linked_spatial_filter.py`
  already demonstrates the spatial-filter logic, so this would be a thin UI variant if another guide wants to
  cross-reference it.

## Operating notes (not for the website)

Another agent mutated the shared main checkout mid-task: `pyproject.toml` briefly contained unresolved merge
conflict markers, the checkout's branch changed under me (`main` -> `mols2grid-3-widget-port-clean`), and
`shinywidgets/_render_widget.py` transiently contained conflict markers too (a `SyntaxError` on import). I did
not touch any of those files. I isolated my own verification work by creating a detached git worktree
(`git worktree add --detach <scratch>/repo-snapshot 38a1796b`) and running every example against that snapshot's
`shinywidgets` package (via `PYTHONPATH`) instead of the live, moving checkout. The coordinator separately
pointed at an official isolated worktree (`scratchpad/main-wt`) partway through; I confirmed it resolves
`shinywidgets` correctly when the working directory is the worktree itself (its editable install's `.pth` points
there), but continued using my own already-working snapshot for the remainder of the task rather than switch
tools mid-verification. All screenshots in `img/` were produced against the pinned, known-good commit
`38a1796b`, which matches the `_ipyleaflet.py` accessor code reviewed above.

## Update 2026-11-11 (main @ 32ca7035)

Updated against `main` @ `32ca7035` (the accessor redesign: #437, #441, plus fixes #398/#405/#415),
per the coordinator's update brief. This guide was originally written against a commit at or before
the redesign (its old text explicitly said "`clicked()` ... is an event (it resets to `None` on
re-render)", matching pre-#437 behavior exactly -- confirmed by diffing `_ipyleaflet.py` at
`02062d60~1` (pre-redesign) vs. current `main`: `CLICKED` was `kind="event"` there, `kind="state"`
now).

### What changed in the guide, and why

- **Accessor reference table**: replaced `fires when` / `None`/not-ready means` with `before any
  interaction` / `across re-render`, matching the new brief's format. Added a paragraph explaining
  *why* each of `bounds()`/`zoom()`/`center()`/`drawn_features()` re-seeds (they describe the map's
  own state, and a re-render is a fresh `Map`) vs. why `clicked()` is kept (it's something the user
  did, not something the map owns).
- **Deleted the event/state framing.** "All five are state accessors except `clicked()`, which is
  an event" is gone -- that taxonomy is no longer user-facing (confirmed: every one of the five is
  declared `kind="state"` in current `_ipyleaflet.py`; the field survives internally but no longer
  drives the re-render reset for any of this renderer's accessors).
- **`clicked()` is now kept across re-renders, not reset.** This is the single biggest behavior
  change for this guide. Verified directly (see below): click the map, force a re-render via an
  unrelated action button, and the previous click's coordinates are still there. Rewrote the
  `clicked()` subsection to state this and removed the old "the docstring says two clicks, but
  Python only sees one -- that's a correction" framing, since the method's docstring on current
  `main` already states the single-publish behavior directly (part of #398's "docstring corrections
  from guide findings"); there's nothing left to correct.
- **Added a "Reading on demand" subsection** (new `examples/16_read_on_demand.py`) per the update
  brief's explicit suggestion for the map guides: a "Save view" button that reads
  `center()`/`zoom()`/`drawn_features()` on click, with nothing else in the app subscribed to those
  accessors. This is most meaningfully new for `clicked()`-shaped accessors (pre-redesign, an
  `event`-kind accessor like the old `clicked()` attached *lazily*, only once something first read
  it -- confirmed in the pre-redesign `_accessors.py`: `on_render` only attached a slot `if
  widget is not None and (slot.spec.eager or slot.activated)`, where `eager = kind == "state"`).
  `bounds()`/`zoom()`/`center()`/`drawn_features()` were already `kind="state"` (eager) before the
  redesign, so for them this is a smaller, confirmatory change rather than a newly-unlocked
  capability; said so in Judgment calls below rather than overclaiming it in the guide body.
- **Gotchas**: reworded the double-click bullet to state the fact plainly (one publish, not two)
  instead of framing it as a docstring correction, for the same reason as the `clicked()` subsection
  above.
- **No `reactive_read(map.widget, ...)` calls existed in this guide** to convert to `.read()` --
  the only `reactive_read()` usages are on a `Marker` layer and a `GeoJSON` layer's trait (child
  widgets), both correctly tier-3 already. Added one sentence explaining why `reactive_read()`
  remains the right tool there (a layer/control isn't the output's own `.widget`, so there's no
  `.read()` for it).
- **Rate limiting section unchanged.** Re-verified: none of the five accessors declares a default
  `rate_policy` in current `_ipyleaflet.py` (unlike lonboard's `view_state()`, which gained one via
  #400) -- the section's claim was already correct and still is.

### New/edited examples, verification status

- `examples/16_read_on_demand.py` -- new. Ran on port 8521 in the worktree; drove a real gesture
  with Playwright (pan the map, draw a triangle with the `DrawControl` -- click three vertices, then
  click "Finish" -- click Save), confirmed the saved entry shows the panned-to `center`, the current
  `zoom`, and `shapes=1`. Screenshots taken and looked at (`img/16_read_on_demand_before.webp`,
  `img/16_read_on_demand_after.webp`).
- Re-verified `clicked()`-kept-across-re-render and `bounds()`/`zoom()`-re-seeded with a throwaway
  probe app (not committed to `examples/`): a map with an unrelated re-render button, plus text
  outputs for `clicked()`/`bounds()`/`zoom()`. Click the map, pan, then click "Re-render":
  ```
  after pan:                bounds=((40.7116...,-74.0865...),(40.7636...,-73.9258...))  zoom=13.0
  AFTER RERENDER clicked:   {'coordinates': [40.7300, -73.9900], ...}   (same as the click -- KEPT)
  AFTER RERENDER bounds:    ((40.70394...,-74.07034...),(40.75597...,-73.90966...))     (RE-SEEDED
                              -- exactly the fresh map's own initial bounds, not the panned-to ones)
  AFTER RERENDER zoom:      13.0   (RE-SEEDED from the new map's own zoom=13 constructor arg)
  ```
  Confirms exactly the brief's claim for all three accessors checked.
- No other example files changed. `01`-`15` and the gallery apps are unaffected by the accessor
  redesign (their code already matched post-redesign behavior for the four accessors that didn't
  change kind; only `clicked()`'s prose needed correction, and no example demonstrates clicking,
  re-rendering, and re-reading in one flow except the new one above).

### Accessor coverage (each confirmed with a real gesture)

Unchanged from the original round for the base behavior (`bounds()`, `zoom()`, `center()`,
`clicked()`, `drawn_features()` all verified with real Playwright gestures in the original examples);
this round added re-render-specific verification for `clicked()`/`bounds()`/`zoom()` (above) and a
new on-demand-read verification for `center()`/`zoom()`/`drawn_features()` together
(`16_read_on_demand.py`).

### Bugs found this round

None new. All previously-reported Gotchas (`base=True` layer ordering, `rectangle={}`/`circle={}`
disabling a draw tool, `basemap_to_tiles()` not setting `base=True`, the `--jp-*` CSS variable
theming wart) are either unaffected by the accessor redesign or still carried as previously
documented; none were re-litigated this round since none relate to accessors or `reactive_read()`.

### Judgment calls for the maintainer to revisit

- **"Read on demand" framed as a smaller change for this guide than for `clicked()` alone.** The
  new example reads `center()`/`zoom()`/`drawn_features()` together with `clicked()` as the
  motivating hook in the prose, even though only `clicked()` actually changed attach timing in this
  redesign (the other four were already eager/state pre-redesign). I judged bundling them into one
  "Save view" example was more useful to a reader than a narrower demo of `clicked()` alone reading
  on demand, since `drawn_features()`/`bounds()` are also natural things to capture on a button
  click, and the guide's own prose is explicit that the *attach-eagerly* guarantee (not a before/after
  behavior change) is what makes the pattern reliable. Flagging in case the maintainer wants the
  example narrowed to just `clicked()` to keep the "this is what changed" story crisper.

## Update 2026-11-11 (Task 8b: "Large data" section)

Added `## Large data` directly after "Coordinating multiple views," per the site-content-gaps plan. No new
example or screenshot: the section states that ipyleaflet has no large-data mode of its own (full data to the
browser, DOM/SVG rendering) beyond the existing marker-clustering example, and points to lonboard (GPU) and
localtileserver (tiles) for the two cases where scale actually matters, plus the new
`articles/performance/article.md#three-approaches-to-large-data` anchor (Task 7, same wave -- unresolved until
that task lands; expected per the task block). `check_docs.py` on this guide: clean except that one expected
unresolved anchor.
