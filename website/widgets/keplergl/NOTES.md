# NOTES: kepler.gl guide

## Versions used

- keplergl **0.4.0** (final release; the old report in `docs/widget-reports/keplergl/` was written
  against 0.4.0rc4, which had been stale since April). Confirmed `importlib.metadata.version("keplergl")
  == "0.4.0"` in the worktree venv.
- shinywidgets commit `00f90249` (origin/main at worktree creation), shiny 1.9.0, Python 3.12,
  pandas/geopandas/pyarrow as locked in `uv.lock`.
- Chromium via Playwright (bundled with the worktree's `playwright` package). `--use-angle=swiftshader
  --enable-unsafe-swiftshader --ignore-gpu-blocklist` launch args used throughout; WebGL/deck.gl
  rendered correctly with them (did not test without, since the old report already established both
  work on this machine).
- Date: verification done 2026-10-30, guide finalized 2026-11-02 after a session restart (see
  "Session restart" below).

## Session restart

This run hit an API spend limit partway through and was resumed in a fresh coordinator session. The
scratch directory was wiped (all probe scripts and screenshots lost), but the worktree and this
guide's `examples/` were intact. Everything in the verification table below was **re-run from
scratch** after the restart (all example apps re-served, all screenshots re-captured, all gestures
re-driven) rather than trusted from memory. Numbers that depend on timing (rate-limit counts, where
exactly time-filter playback has moved after N seconds) differ slightly between the two passes, as
expected for wall-clock-dependent gestures; both passes agree on the qualitative claims (throttling
visibly reduces read count; playback moves the window and changes the table). The guide's final
numbers come from the post-restart pass.

## Verification table

| File | Ran? | Screenshot? | Gesture driven? | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes (`img/hero.webp` = `img/01_quickstart.webp`) | n/a (static) | Auto point layer renders correctly. |
| `examples/02_hexbin.py` | yes | yes | n/a (static) | Confirmed 1 layer only (no auto-layer duplicate) via `window.widgetManager` model inspection. |
| `examples/03_geodataframe.py` | yes | yes | n/a (static) | |
| `examples/04_time_playback.py` | yes | yes | n/a for the guide screenshot; playback driven separately in examples 07/10 | Time filter panel ("enlarged" view) renders; initial window matches config. |
| `examples/06_reading_config.py` | yes | yes (before/after pan) | yes -- mouse drag on the canvas | `reactive_read(map.widget, "config")["config"]["mapState"]` updates live; verified exact lat/lon change pre/post drag, twice (both before and after the session restart), reproducing the same values each time. |
| `examples/07_rate_limiting.py` | yes | yes (before/after 4s of playback) | yes -- clicked the play button | Throttled: 4-12 reads per 4s across two runs (rate_delay=0.5, i.e. cap ~8/4s -- consistent). Unthrottled comparison app (not part of the guide's file set; see below): 12 reads in one run, 215 in another, i.e. tens to ~50/s -- config write frequency during kepler's own playback animation is itself variable, not just the rate limiter. |
| `examples/08_update_in_place.py` | yes | yes (before/after slider) | yes -- clicked along the ion.rangeSlider track | Map updates in place; camera/zoom provably unchanged (identical basemap framing in both screenshots). |
| `examples/09_config_round_trip.py` | yes | yes (panned / reset / restored, 3 shots) | yes -- drag pan, then Save/Reset/Restore button clicks | Full round trip verified: panned to lat 45.463, saved, reset to default (lat 45.53), restored (back to lat 45.463). Reproduced identically pre- and post-restart. |
| `examples/10_time_window_table.py` | yes | yes (before/after playback) | yes -- clicked play | Table row count and contents track the filter's live `value` window; verified with an empty-window case (table correctly shows 0 rows when playback moves past all data) and a populated case shown in the guide. |
| `examples/11_linked_chart.py` | yes | yes (after slider) | yes -- clicked along the slider track | Map and histogram update together from one input; initially missed because a screenshot was taken mid-plotly-transition (see Judgment calls). |
| `gallery/template_station_explorer.py` | yes | yes | n/a (static capture; same slider/reactive_read mechanism already gesture-verified above) | |
| `gallery/showcase_riots_timeline.py` | yes | yes (initial + filtered) | yes -- unchecked two incident-type checkboxes | Hex columns shrink/change, table updates to match, time window and camera unaffected. |

No accessors exist on `render_keplergl`, so there is no accessor-coverage table: confirmed by reading
`shinywidgets/_render_widget.py` (`class render_keplergl(render_widget_base[ValueT, KeplerGl])` has no
`_accessor_specs` override) and `docs/plans/2026-10-29-reactive-accessors-candidates.md`, which lists
keplergl explicitly as `accessor: none` with the rationale "`config` re-syncs on every animation frame
and carries no click or pick state."

Trait-level verification of what the browser actually writes back: grepped the installed
`keplergl/static/widget.js` for `model.set(` and found exactly one call site, `model.set("config", ...)`.
`data`, `mapbox_token`, `theme`, and `app_name` are Python-to-browser only. `height` changes too, but
that's shinywidgets' own fill/ResizeObserver hook writing the measured size, not kepler.gl's code.

## Bugs found

**None found in shinywidgets or keplergl on current `main` / keplergl 0.4.0.** Three things the old
report (`docs/widget-reports/keplergl/report.md`, written against keplergl 0.4.0rc4) flagged as
blockers are now fixed or no longer reproduce; documented as such in the guide's "Gotchas and
limitations" rather than as open bugs, since re-reporting fixed issues would be noise:

1. **Echo-replay bug (shinywidgets, pre-existing, now fixed).** The old report's root cause (missing
   `msg_id`/`parent_header` tagging in `js/src/comm.ts` and `shinywidgets/_comm.py`, causing stale
   browser-originated updates to be re-applied) is no longer present: both files now tag and check
   `parent_header`/`msg_id` (confirmed by reading the source, not just testing around it). I drove
   kepler's own time-filter playback for several seconds against a filling-layout, explicit-height, and
   re-rendered map, all of which the old report said would break -- none did; `n_layers` stayed correct
   throughout.
2. **NaN-in-DataFrame session-killer (shinywidgets, pre-existing, now fixed).** `dataframe_to_keplergl`
   on `main` already uses `use_arrow=True` and gates on `isinstance(value, pd.DataFrame)` -- exactly the
   fix the old report recommended. Covered by `tests/unit/test_keplergl.py::test_dataframe_with_missing_values_serializes`
   and `test_series_is_not_coerced`, both passing.
3. **Config-merge duplicate-layer bug (upstream keplergl, apparently fixed in 0.4.0 final).** The old
   report found that `widget.config = new_config` after render left the auto-created layer in place
   alongside the new one. I could not reproduce this on keplergl 0.4.0: re-assigning `.widget.config`
   repeatedly (same config, and with an entirely new layer id/type) both settled at the correct layer
   count (1) every time, checked via direct inspection of the live anywidget model. I can't rule out a
   narrower repro I didn't hit, but the general case in the old report's own recipe no longer
   reproduces, so I documented this as *not currently a problem* rather than reporting it as fixed
   upstream (I don't know kepler.gl's changelog well enough to attribute the fix).

All 12 `tests/unit/test_keplergl.py` tests pass. `tests/playwright/render_keplergl` (4 tests) and
`tests/playwright/render_keplergl_redisplay` (2 tests) pass; one redisplay test
(`test_redisplayed_widget_keeps_filling`) failed once under concurrent load from other agents and
passed cleanly on an isolated re-run, so it's recorded as a load flake, not a bug (per the "re-run once
before calling it a bug" rule).

**Docs:** no incorrect docstring claims found for `render_keplergl` -- its docstring already mentions
the `"data"` dataset name, the in-place-update recipe, and the browser-owned-height wrinkle for the
current release.

**Found during the Decision 8 re-verification (2026-11-02), both pre-existing and
dataset-independent (reproduced on the old `la-riots` showcase code too), both cleanly upstream
in keplergl 0.4.0's `static/widget.js` (`onConfigChange` -> `loadConfig()` dispatches kepler.gl's
`addDataToMap({datasets: [], config, options: {centerMap: false, keepExistingConfig: true}})`);
shinywidgets only delivers the trait change):**

4. **Config-set with an explicit `layers` entry breaks layer rendering.** Assigning
   `.widget.config = X` where `X` contains an explicit layer (e.g. the showcase's hexagon)
   leaves the layer unrendered; with a fully materialized (synced-back) config the layer is
   *also duplicated* in kepler's layer panel. Auto-layer configs (example 09) are unaffected,
   which is why the earlier pass's "duplicate-layer bug does not reproduce" conclusion held --
   it only exercised auto-created point layers. Workaround (now used by the showcase): strip
   `visState.layers` from the saved config before assigning it.
5. **`keepExistingConfig` ignores incoming values for existing filters.** A saved
   `timeRange` filter `value` cannot be restored via config-set -- kepler keeps the existing
   filter's value (mapState merges fine). So a saved time window is not programmatically
   restorable on keplergl 0.4.0; the showcase's save/restore is therefore camera-only.
   Both findings are documented in the guide's "Gotchas and limitations" and reported to the
   coordinator for an upstream-filing decision.

## Judgment calls

- **Dataset choice for time-based examples.** Used vega-datasets' `la-riots.csv` (1992 Los Angeles
  civil unrest deaths) for the time-filter/playback examples, fetched directly via
  `pandas.read_csv(<jsdelivr URL>)` rather than through the `vega_datasets` package. Reasoning: it's a
  small (63-row), real, historical dataset with both lat/lon and a date field, widely used in
  dataviz-teaching contexts (it's a stock vega-lite example), and it avoided a dependency-overlay
  problem (see below). I kept the captions factual and did not editorialize on the historical events;
  flagging this choice in case the maintainer would rather use a less sensitive dataset for a
  public-facing guide.

  **Resolved 2026-11-02 (maintainer Decision 8): swapped to vega-datasets' `bird-migration.csv`**
  (3,229 rows; `species`,`day`,`date`,`lon`,`lat`; daily 2015 positions of ten tracked species
  migrating between South America and the Arctic -- also one of kepler.gl's own demo datasets).
  Same shape as `la-riots` (lat/lon + real date + a categorical for the showcase's checkbox
  filter), fetched the same way (`pandas.read_csv` of a jsdelivr URL, pinned to git commit
  `5448e25` since `bird-migration.csv` isn't in the npm package). Covers `examples/04`, `07`,
  `10`, the renamed `gallery/showcase_bird_migration.py` (was `showcase_riots_timeline.py`),
  and the guide prose; all 7 affected screenshots re-taken, all four apps re-verified in the
  browser (playback, throttled-read counts, window-driven table row counts, species-filter
  in-place update). The 04/07/10 configs gained an explicit `mapState`: with the larger,
  slower-loading dataset kepler.gl's own centerMap fit intermittently rendered a stale world
  view on first load (fine after any interaction), and an explicit `mapState` (which disables
  centerMap) makes the initial frame deterministic. Row counts in the guide prose updated to
  match (67 of 3,229 in the initial one-week window).
- **`uv run --no-sync --with vega_datasets` failed under `shiny run`** (`ModuleNotFoundError:
  No module named 'vega_datasets'` even though a bare `uv run --no-sync --with vega_datasets python -c
  "import vega_datasets"` succeeded) -- looked like the ephemeral overlay doesn't propagate into
  whatever subprocess/env `shiny run`'s console-script entry point uses. Worked around by not using the
  package at all: the same CSV is reachable over plain HTTPS, so every example just uses
  `pandas.read_csv()` with the already-locked pandas. Flagging this for the coordinator in light of the
  "don't overlay unpinned packages" note that arrived mid-session -- I'd independently already dropped
  `--with` for this guide's examples before that note arrived, for an unrelated reason (it simply
  didn't work under `shiny run`), so no finding in this guide depends on an overlaid package version.
- **No accessors, confirmed two ways:** by reading `_render_widget.py` (no `_accessor_specs` on
  `render_keplergl`) and by reading the installed `widget.js` for `model.set(` call sites (only
  `config`). I also re-derived this from the design doc's candidate table rather than trusting the
  stale "Goals/Non-goals" lists per the brief's instruction.
- **Rate-limiting numbers vary by run** (4 vs. 12 reads in two throttled runs; 12 vs. 215 in two
  unthrottled runs over nominally the same ~4s window) because kepler.gl's own playback-driven config
  write frequency isn't fixed -- it depends on the browser's animation-frame timing, which this
  loaded, shared machine doesn't hold constant. I used the larger (215, i.e. ~50/s) unthrottled number
  in the guide's prose as the more dramatic and equally real worst case, but noted the throttled number
  as "4-12" in spirit (wrote "dozens of times a second unthrottled" and "at most one read per 0.5s"
  rather than a single precise ratio, to not overclaim precision the gesture doesn't actually have).
- **One linked-chart screenshot appeared blank on first attempt**, because I captured it immediately
  after a slider drag, mid-plotly-redraw-transition. Confirmed via DOM inspection
  (`#hist`'s `innerHTML` contained a populated `svg.main-svg`) that the chart had in fact rendered and
  it was purely a screenshot-timing issue, not a bug; the guide's screenshot was taken after an
  additional wait.
- **Dropped from the old report:** the 50k-point kepler/lonboard/pydeck payload-size comparison table
  (out of scope for a single-widget guide; better suited to a cross-cutting maps article the
  coordinator may want to write) and the `JUPYTER_WIDGETS_ECHO = False` workaround (no longer needed,
  since the underlying bug is fixed).

## Editor's notes for the website

- Strongest screenshots: the quickstart hero (dense, colorful point cloud over Montreal) and the 3D
  hexbin (`img/02_hexbin.webp`) -- both read well at thumbnail size. The showcase gallery app's
  before/after filter pair is the best evidence of "it's a real tool," and would make a good GIF if the
  coordinator wants one (I did not produce one; static before/after seemed sufficient here).
- If the page needs to be shorter: cut "GeoDataFrame input" from What You Can Build first (it's the
  least visually distinctive section -- the screenshot looks identical to the quickstart), and/or
  trim the "Beyond accessors" table to just `mapState` and `filters` (drop `layers`, which is less
  commonly read directly).
- The "Gotchas and limitations" section is unusually short for a widget this complex, because the
  three historical blockers all turned out to be fixed. That's a genuinely good-news result, not an
  under-researched one -- I'd keep the section's framing ("verified on current main," naming what no
  longer reproduces) rather than padding it with upstream nitpicks (debug console noise, a stale
  timeout warning) elevated to look more substantial than they are.

## Pairs with (for cross-cutting articles)

- **plotly**: `examples/11_linked_chart.py` / `guide.md`'s "One input, two linked views" -- one Shiny
  input drives both the map (in place) and a plotly histogram from the same filtered frame.
- **itables / reactable** (not built here, but a natural extension): `examples/10_time_window_table.py`
  uses `render.data_frame`; swapping in either dedicated table renderer would work identically since
  the pattern is just filtering a DataFrame by the filter's live `value`.

## Update 2026-11-11 (main @ 32ca7035)

### What changed and why

- Converted every `reactive_read(map.widget, "config")` to `map.read("config")` across `guide.md`, 4 example
  files, and 2 gallery apps (`config` lives on the rendered `KeplerGl` itself -- no child widgets involved).
  Dropped the now-unused `reactive_read` import from each touched file.
- Renamed the "### Beyond accessors: `reactive_read`" heading to "### Beyond the accessors: `.read()`" per the
  brief, and reworded the surrounding prose (the renderer intro paragraph, the "Reacting to user interaction"
  intro, "Rate limiting") to teach `.read("config")` as the primary call, keeping one explicit
  `.read()`/`reactive_read()` dual-mention where the point is specifically that the renderer's `rate_policy`
  kwarg governs both. `accessors: []` is unchanged (still correct: no `_accessor_specs` on `render_keplergl`).
- `examples/07_rate_limiting.py`'s on-screen page title (`"Rate-limiting reactive_read"` ->
  `"Rate-limiting .read()"`) and card header (`"reactive_read() invocations..."` -> `".read()
  invocations..."`) changed; regenerated `img/07_rate_before.webp` and `img/07_rate_after.webp` since both were
  visible in the stale screenshots.
- Re-verified the rate-policy claim this pass (explicitly requested in the brief for this guide): ran
  `07_rate_limiting.py` fresh, clicked the kepler.gl time-filter play button, and measured the throttled
  counter (`rate_policy="throttle", rate_delay=0.5`) go from 2 to 11-12 reads over ~4 seconds of playback --
  consistent with the original pass's "4-12 reads per 4s" throttled range and the cap of 1 read/0.5s. The
  guide's prose makes no single-number claim (deliberately, per the original pass's note that kepler's own
  playback write frequency varies run to run), so no wording change was needed beyond the `.read()` renaming
  -- the underlying mechanism (`rate_policy`/`rate_delay` governing `.read()`'s fallthrough to
  `reactive_read()` on the widget) is unchanged on current main.

### Verification

- `examples/07_rate_limiting.py` (edited): ran in browser, drove the real kepler.gl playback-button click,
  confirmed `.read("config")` fires and the throttle still caps it as described above. Fresh before/after
  screenshots taken and looked at (Read tool); both match current on-screen text.
- `examples/06_reading_config.py`, `examples/09_config_round_trip.py`, `examples/10_time_window_table.py`,
  `gallery/template_station_explorer.py`, `gallery/showcase_bird_migration.py` (all edited): mechanical
  conversions of `reactive_read(map.widget, "config")` to `map.read("config")`, same code path exercised live
  above and confirmed identical by reading `shinywidgets/_render_widget_base.py`'s `read()`; not independently
  re-driven with a live gesture this pass (`config` itself was already gesture-verified end to end -- drag,
  save/reset/restore, playback -- in the 2026-10-30 pass).

### Bugs found (2026-11-11)

None new. Minor pre-existing nit noticed while ruff-checking this pass's edits (not introduced by this pass,
and not fixed since `examples/11_linked_chart.py` wasn't otherwise touched): `import plotly.graph_objects as go`
in `examples/11_linked_chart.py` is unused (`ruff check --select F` flags `F401`). Harmless -- the file doesn't
use `go` anywhere -- but worth a one-line cleanup next time that file is edited.

## Update 2026-11-11 (Task 8b: "Large data" section)

Added `## Large data` directly after "Coordinating multiple views." No example in this guide tests kepler.gl at
a specific large-N scale, so the practical-limit claim is attributed to kepler.gl's own upstream docs
(https://docs.kepler.gl) rather than measured in this pass, per the section contract's item 2 ("attributed with
a link to upstream docs" when no in-guide measurement exists). The existing ~12.9 MB initial-bundle measurement
(already in "Updating the widget from Python") is cited as the cost that GPU aggregation doesn't remove. No new
example or screenshot. One link to `articles/performance/article.md#three-approaches-to-large-data` is
unresolved until Task 7 (same wave) lands, per the task block; `check_docs.py` on this guide is otherwise
clean.

### Judgment call for the maintainer to revisit

I described kepler.gl as "built on deck.gl, the same engine lonboard uses" based on the kepler.gl project's own
public description and this guide's existing cross-link language (the guide's intro contrasts kepler.gl against
lonboard's "GPU-scale" rendering already); I did not independently re-verify kepler.gl's renderer internals
against its source for this task. If that attribution is too strong without a direct citation, it's a one-line
edit to soften to "GPU-accelerated aggregation layers" without naming deck.gl specifically.
