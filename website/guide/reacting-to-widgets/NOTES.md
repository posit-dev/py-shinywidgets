# NOTES: "Reacting to widgets" article

## Versions

- shinywidgets: `main` @ `00f90249` (2026-10-30), run from the coordinator's detached worktree.
- shiny: 1.9.0
- plotly: 6.9.0, ipyleaflet: 0.20.0, altair: 6.3.0, k3d: 3.2.0, ipydatagrid: 1.4.0, bqplot: 0.13.1
- Playwright: Chromium, headless, 1280x800-ish viewports per example (noted below), `device_scale_factor=2`
- Date: 2026-10-30

## Verification table

Every example was run with `uv run --no-sync shiny run <file>` from the worktree and driven with Python
Playwright (sync API); every screenshot referenced in `article.md` was read back with the Read tool before
being cited.

| File | Ran | Screenshot | Gesture driven | Confirmed |
|---|---|---|---|---|
| `examples/01_mental_model.py` | yes | before/after | zoom-in x2 (control click) + pan drag | `map.zoom()`/`map.center()` and `reactive_read()` report identical values after the gesture |
| `examples/02_not_rendered_none_state.py` | yes | before/after-click/after-rerender | click (ipyleaflet), drag-brush (altair), page load (k3d auto-fit) | `camera()` not-ready->populated; `clicked()` None->value->None on re-render; `selected()` empty->populated, never None |
| `examples/03_refire_and_clearing.py` | yes | same-point/dblclick-marker/dblclick-background | click same marker twice, click different marker, dblclick marker, dblclick background | fire counts: +0 (same point), +1 (different point), +2 (dblclick on marker: clear then re-set), +1 (dblclick on background: clear only) |
| `examples/04_rate_limiting.py` | yes | before/after | slow multi-step box-drag (plotly x2), 5 rapid row clicks (ipydatagrid x2) | plotly: 2 vs. 7 fires (debounce vs. `rate_delay=0`); ipydatagrid: 6 vs. 6 fires (kwarg has zero effect on the accessor either way) |
| `examples/05_rows_of_data.py` | yes | before/after | box-select drag | `selected_rows(df)` -- matched via `custom_data=[df.index]`, verified non-empty, index-matched rows shown in `render.data_frame` |
| `examples/06_writing_back.py` | yes | before/after | zoom-in x2, 3 map clicks | 3 markers added in place; zoom level unchanged after all 3 writes; counter correct (no loop, `reactive.isolate()` used) |
| `examples/07_lifetimes.py` | yes | zoomed / after-rerender | zoom-in x3 on two panels, then click "Re-render" | default-lifetime map visibly resets to its construction-time view; `session_lifetime()` map visibly keeps the zoomed view |
| `examples/07_lifetimes.py` + `examples/globals.py` (shared_lifetime, 2 browser contexts) | yes | tabA/tabB before+after | zoom-in x3 in tab A only | tab B's map visibly mirrors tab A's zoom with no interaction of its own, confirming cross-session mirroring once the widget is constructed in `globals.py` (see Bugs/judgment calls below for the broken version) |

No accessor in this article's examples was impossible to automate; all gestures were real mouse events
(`page.mouse.move/down/up/click/dblclick`) or real clicks on rendered controls (leaflet zoom buttons, a
Shiny action button), never a JS-level trait assignment.

## Bugs found / surprises

- **[authoring hazard, verified independently]** `examples/06_writing_back.py`'s comment documents the
  infinite-loop trap precisely because I nearly wrote it: an effect that both reads and sets a counter
  reactive value (`clicks.set(clicks() + 1)`) without `reactive.isolate()` makes the effect depend on its
  own output, so setting it reschedules itself forever -- no error, no visible symptom beyond pinned CPU.
  This matches the itables guide's independently-discovered "authoring hazard" finding in
  `docs/widget-guides/FINDINGS.md`. Not re-triggered live here (deliberately -- see Judgment calls).
- **[sw/docs] `render_plotly.clicked()`'s docstring is imprecise**, confirmed with a fresh, precise repro
  (`examples/03_refire_and_clearing.py`): "a double-click clears it" is only true when the second click
  lands on background. On a marker, the clear (`plotly_doubleclick`) and the re-set (`plotly_click` on that
  marker) both fire -- 2 reactive invalidations, net value unchanged -- not the 0 invalidations "unchanged"
  might suggest. This refines (doesn't contradict) the plotly guide's own already-reported version of this
  finding; I independently reproduced the exact fire-count mechanism (+2, not +0 or +1) rather than just the
  end-state.
- **[test-app bug, not shinywidgets]** My first version of `examples/07_lifetimes.py` built
  `THE_SHARED_MAP` with `with shared_lifetime(): ...` directly at the top level of the Express script. Two
  browser tabs against that version never mirrored each other's zoom -- not even after a 4-second wait, and
  not even for a *Python-side* `effect`-triggered `.zoom = 14` write (confirmed via `reactive_read()` in the
  second tab's own session, which never invalidated, and via a screenshot of the second tab's actual map,
  which never moved). Root cause, confirmed by reading `shiny/express/_run.py`: Shiny Express recompiles and
  re-executes the *entire app file* once per session (`run_express()` is called from `express_server()`, the
  per-session server function) -- so a `shared_lifetime()` call directly in the script body still runs once
  per session, constructing an independent `Map` instance each time, no different from the un-decorated
  default lifetime. `shared_lifetime()`'s own docstring already warns about exactly this ("the body of a
  Shiny Express app file... runs once per session"), and Express has an officially-supported escape hatch
  for it -- a sibling `globals.py` file, which `create_express_app()` imports (later correction: not "exactly once" -- Express can run `globals.py` at least twice per process, intentionally; see the pygwalker NOTES.md double-execution finding. The article and `examples/globals.py` were reworded to "at least once, write idempotent setup"; noted here so this stale claim isn't re-quoted) before any
  session exists (`shiny/express/_run.py`, the `globals_file` branch). Moving the construction into
  `examples/globals.py` fixed the cross-session mirroring completely (see the verification table). I'm
  reporting this as a **sharp edge in `shared_lifetime()` + Shiny Express interaction**, not a shinywidgets
  bug -- the docstring already contains the warning, but it's easy to read past, and (as far as I can tell
  from the other guides) no finished guide has run into or documented it yet with a worked repro. Worth the
  maintainer considering whether `shared_lifetime()` could detect and raise on this (e.g., warn if called
  more than once for what looks like the same call site across sessions) rather than silently constructing
  independent widgets.
- **[cross-cutting, independently reconfirmed]** The `rate_policy`/`rate_delay` renderer kwargs only affect
  accessors that declare a default rate policy, plus `reactive_read()` on `.widget`. `examples/04_rate_limiting.py`
  reconfirms this precisely for `render_ipydatagrid`'s `selected()` (already found by the ipydatagrid
  guide) by putting it side by side with `render_plotly`'s `selecting()` (which *does* have a default) in
  one app, so the contrast is visible in a single screenshot rather than two separate guides' numbers.
- **[confirmed, not re-fixed]** `render_reactable` sets `accessor_specs` (missing leading underscore)
  instead of `_accessor_specs` at `shinywidgets/_render_widget.py:5329` on this commit, so all 5 of its
  accessors raise `KeyError`. Already reported in `docs/widget-guides/FINDINGS.md` with a local fix branch;
  the cheat sheet documents the *intended* behavior and flags the regression prominently rather than
  pretending it works.

## Judgment calls

- I did not actually let the infinite-loop effect run (described in "Writing back" and in `06_writing_back.py`'s
  comment) to produce a "frozen app" screenshot -- doing so would pin a CPU core on a shared, loaded machine
  for no screenshot anyone could usefully look at (a frozen app looks identical to a slow one). I verified
  the *mechanism* by reading `shiny.reactive`'s dependency-tracking semantics and by cross-referencing the
  itables guide's independently-discovered live repro of the same pattern (cited in `FINDINGS.md`), and
  wrote the correct (isolated) version as the only one that actually runs. A second opinion on whether the
  coordinator wants a deliberately-hung demo captured anyway (e.g., with a hard timeout and a "CPU pinned"
  annotation) would be welcome, but I judged the risk/benefit not worth it given the shared machine.
  Original claim per the brief's FINDINGS.md pointer (itables guide): "An unguarded `@reactive.effect` doing
  `count.set(count() + 1)` loops forever and silently freezes the whole app."
- `examples/05_rows_of_data.py`'s box-select over a dense cluster of the `tips` dataset selected 152 of 244
  rows -- more than it looks like from the scatter plot, because many points overlap exactly (restaurant
  bills/tips repeat). I kept the example as built rather than picking a smaller, cherry-picked box, since
  the point (customdata-matched rows, correctly filtered) holds regardless of count, and a real "it's bigger
  than it looks" data quirk is more honest than a staged small selection.
- I used ipyleaflet for three of the seven examples (mental model, not-rendered/None/state, writing back,
  lifetimes -- four, actually). This was deliberate: ipyleaflet's accessors are simple, fast to render, and
  camera-based interaction (zoom/pan) is the clearest way to show "value preserved vs. reset" visually across
  several different points (mental model, writing-back, lifetimes). A second opinion on diversifying the
  widget choice further (e.g., swapping one ipyleaflet example for a geospatial-adjacent one like lonboard)
  would be reasonable if the coordinator wants less repetition across this article's own screenshots -- I
  leaned toward consistency because it let me reuse the same zoom-button/drag-pan driving code across
  examples, and because the per-widget guides already cover far more breadth than this article needs to.
- Mosaic and bqplot's own already-published rate-limiting/reactive_read examples are cited by link rather
  than rebuilt here, per the brief's "don't duplicate a guide's content; summarize and link" instruction.
  I re-read (did not re-run) those guides' relevant sections to confirm the citations are accurate as
  written; I did not re-verify their screenshots myself.
- Panel/holoviews: both guides are incomplete on the roster as of this writing (no `guide.md` yet in either
  directory, only partial `examples/`). The brief says to use their established recipe for param-based
  libraries "if the guides establish one; otherwise point to them" -- I pointed to them rather than
  inventing a recipe myself, since the per-widget guide is the right place to establish and verify it first.

## What I dropped / scoped out

- mols2grid: this worktree (`origin/main` @ `00f90249`) predates the `mols2grid-3-widget-port-clean` branch's
  rework of `render_mols2grid` (the currently-checked-out branch in the main checkout, per the environment
  note in `FINDINGS.md`). The cheat sheet documents mols2grid's accessors as they exist on this commit (the
  authoritative "main" per this task's operating rules), not the in-flight port. If the port changes the
  accessor shapes, the cheat sheet's mols2grid section will need a follow-up pass once that branch lands.
- I did not build a dedicated example for every widget in the cheat sheet -- that's intentionally the job of
  each widget's own guide. This article's examples exist only to demonstrate the *cross-cutting* pattern
  (mental model, not-rendered/None/state, re-fire/clearing, rate limiting, rows-of-data, writing back,
  lifetimes) with the smallest, clearest widget for each point, then link to the guides for breadth.

## Editor's notes for the website

- Strongest material: "Rate limiting" (the 2-vs-7-vs-6-vs-6 four-panel screenshot is a single image that
  makes the entire cross-cutting finding legible at a glance) and "Lifetimes" (the `shared_lifetime()` +
  Express gotcha, with its before/after/tabA/tabB screenshots, is both correct and a genuinely new
  contribution -- no other guide had documented this trap with a live repro as of this writing).
- The "mental model" section's screenshot is the least visually interesting (two near-identical text panels)
  but is cheap to keep; it's doing conceptual work, not visual work.
- If the page needs to be shortened, the "Rows of your data" section could drop to a single sentence plus
  the bullet list of per-library links -- the plotly customdata snippet is useful but the concept is fully
  covered in each widget's own guide already.
- Hero image candidate: `img/04_rate_limiting_after.webp` (set as `hero` in the front matter) -- it's the
  single image that most concretely shows *why this release's headline feature matters* (a measurable,
  visible difference in behavior driven by one kwarg, across two different widget families).

## Update 2026-11-11 (main @ 32ca7035)

Rebased on `main` @ `32ca7035` (up from `00f90249`), after the reactive-accessor redesign (#412, #419, #428,
#437, #441, #443 and friends). Read the PR bodies for #437, #412, #419, #441 in full before writing. This was
a restructure, not a patch: the old event/state taxonomy, "resets to `None` on re-render", "attaches on first
read", and the warm-up idiom are gone from the article and cheat sheet -- they no longer describe current
`main`, and the brief's "delete, don't soften" instruction applies literally (no "what changed" section was
added; the guide describes current behavior only).

### What changed in the article, and why

- **"The mental model" rebuilt** around the one behavior (#437): attaches at render, records interactions
  whether or not anything has read them, kept or re-seeded across re-renders. Kept `examples/01_mental_model.py`
  (ipyleaflet `zoom()`/`center()` vs. `reactive_read()`) since it's still an accurate, simple illustration of
  "accessor reads like an input"; reframed the prose around it rather than making accessor-vs-`reactive_read`
  the section's whole point (that comparison now lives in "Beyond the accessors").
- **"'Not rendered yet' vs. `None` vs. always-a-value" renamed "Before the first interaction"** and rebuilt
  with four states (cancels / `None` / `[]`/`{}` / seeded) instead of three. The old ipyleaflet-`clicked()`
  "resets to `None` on re-render" claim (verified false -- `clicked()` is `kind="state"`, and its `attach`
  never seeds, so it's kept) is gone; the re-render half of that story now lives entirely in the new "Across
  re-renders" section. Swapped in bokeh's `selected()` (now `[]`, not `None` -- #437) as the fourth state, new
  example app `examples/02_not_rendered_none_state.py` (filename kept, content rewritten; four widgets: k3d
  `camera()` cancels, ipyleaflet `clicked()` is `None`, bokeh `selected()` is `[]`, altair `selected()` is
  seeded). New screenshots `img/02_states_before.webp` / `img/02_states_after.webp`; the old
  `02_states_after_click.webp` / `02_states_after_rerender.webp` (which showed the now-false re-render-resets
  claim) were deleted.
- **New section "Across re-renders"**, new file `examples/08_across_rerenders.py`: `clicked()` (kept) and
  `zoom()`/`center()` (re-seeded) side by side on the same ipyleaflet map, with a re-render button. Includes
  the "a kept payload can describe the previous render's widget, prefer ID-keyed lookups" caveat, cited
  against plotly's `clicked()` and ipydatagrid's `edited_cell()` docstrings rather than built as a second
  live repro (the docstrings already state the mechanism precisely; a second contrived data-mismatch demo
  would have added an example without adding a new verified fact).
- **"Attaching early: the first-read gotcha" replaced by "Read on demand"**, the headline new capability
  (#412/#419 -- lazy attach and the warm-up idiom are gone entirely; `AccessorSpec` has no `eager` field on
  current `main`, confirmed by reading `shinywidgets/_accessors.py`). New file
  `examples/09_read_on_demand.py`: a plotly lasso/box selection made before anything reads it, revealed
  intact by a button click gated with `@reactive.event` -- no warm-up effect anywhere in the file. Mentions
  chat/LLM tools in prose and links to `../ai-exploration/article.md` (did not duplicate that article's own
  chat example here, per the brief's "summarize and link" convention for the guides roster).
- **"Re-firing and clearing"**: re-verified the existing plotly `clicked()` fire-count table end to end
  (still accurate: same-point dedup, different-point +1, marker double-click +2, background double-click +1).
  Added a pulse-style accessor as the brief asked: `double_clicked()` (`priority="event"`, never dedupes) in
  the same example file, same figure, new card. Verified precisely: a *second*, separate background
  double-click leaves `clicked()`'s fire count unchanged (already `None`, deduped) while `double_clicked()`'s
  advances again -- the exact contrast the section is making. New screenshot
  `img/03_dblclick_background2.webp`; `03_same_point.webp`/`03_dblclick_marker.webp`/`03_dblclick_background.webp`
  regenerated against the revised (two-accessor) app.
- **"Rate limiting"**: the old contrast (plotly `selecting()` vs. ipydatagrid `selected()`, "no default
  policy") is stale -- `selected()` now debounces by default (#400). Replaced the "no policy" side with k3d
  `camera()` (still genuinely undeclared on current `main`; confirmed via `shinywidgets/_k3d.py`). Rewrote
  `examples/04_rate_limiting.py` with two k3d panels (`rate_delay=0` vs. `rate_delay=2`) replacing the two
  ipydatagrid panels, driven by a slow orbit-drag (k3d's own upstream throttle is ~200ms, so a ~1s drag with
  180ms steps produces several distinct fires). Verified both k3d panels land on the identical fire count (7
  and 7) regardless of `rate_delay`, while the two plotly panels still diverge sharply (3 vs. 8).
- **"Rows of your data"**: dropped the "the reactable guide's accessors are currently dead on `main`" note --
  the underlying `_accessor_specs` typo (missing leading underscore) is fixed on current `main` (confirmed:
  `grep -n "accessor_specs\s*=" shinywidgets/_render_widget.py` shows only the correctly-named
  `_accessor_specs =` assignments now). No other changes needed; example and screenshot untouched (no new
  behavioral claim was added for this section).
- **"Beyond the accessors" rebuilt as "Beyond the accessors: `.read()` and `reactive_read()`"**, teaching
  `.read(name)` first (#437's new per-output method) and narrowing `reactive_read()`'s own teaching to child/
  nested widgets only, as the brief specified. New file `examples/10_read_method.py`: `map.read("zoom")`
  (accessor by name), `map.read("scroll_wheel_zoom")` (bare synced trait, no accessor -- the fallback), and
  `map.read("zooom")` (deliberate typo) live, with the exact raised `AttributeError` text (including the
  "Did you mean 'zoom'?" hint) rendered to the page and screenshotted. Kept the lonboard/bqplot
  `reactive_read()`-on-a-child-widget recipes as links only (unchanged, still the right home for them per the
  brief's "don't duplicate a guide's content" instruction) and added a one-line pointer to panel's new
  `param(name)` accessor as the now-covered case for the param-based-libraries paragraph.
- **"Lifetimes"**: `shared_lifetime()` is now marked **experimental** in the bullet list, matching its own
  docstring (`shinywidgets/_shinywidgets.py`'s `shared_lifetime()`, which now opens with "Experimental: not
  every widget package behaves well..."; PR #442). No other changes -- the Express re-run sharp edge and its
  repro are unaffected by the accessor redesign and were left as-is (not re-run; no new claim was added about
  them).
- **Cheat sheet rebuilt**: dropped the "Kind" column (the event/state split that justified it is gone for
  user-facing accessors; `kind="event"` now only exists as internal plumbing, e.g. bokeh's `source_data`
  trigger) and the "eager" callouts (the field no longer exists on `AccessorSpec`). Added "Before any
  interaction" (cancels / `None` / `[]`/`{}` / seeded) and "Across re-render" (kept / re-seeded) columns,
  determined per accessor by reading every `attach_*` function in every `shinywidgets/_<lib>.py` module (not
  inferred from the PR bodies' example lists, which aren't exhaustive): an accessor whose `attach` function
  calls `emit(...)` synchronously (not from inside a later change handler) is re-seeded; one that only
  registers a listener for future events is kept. Cross-checked every accessor's classification against the
  explicit examples in #437's PR body where it gave one (bokeh/ipyaladin/niivue/lonboard/altair/jscatter/
  bqplot/cytoscape/perspective/reactable are reseed; nothing in that list contradicted the mechanical rule).
  Updated renames (ipycytoscape `clicked_node()`/`clicked_edge()`, ipydatagrid `clicked_cell()`, #441),
  ipydatagrid `selected()` and lonboard `view_state()`'s new default debounce (#400), bokeh `selected()`
  returning `[]` (#437), and the reactable regression note (removed -- fixed).
- Front matter: added `bokeh` to `widgets:` (used in the revised "Before the first interaction" example);
  changed `hero` to `img/08_across_rerenders_before.webp` (the new "Across re-renders" screenshot is the
  single clearest illustration of this release's actual behavior change, more so than the rate-limiting
  screenshot, which demonstrates a narrower point).

### New/edited examples -- verification status

| File | Edited/new | Ran | Gesture driven | Accessor confirmed | Screenshot looked at |
|---|---|---|---|---|---|
| `examples/01_mental_model.py` | unedited | not re-run (no new claim) | -- | -- | reused existing `01_mental_model_after.webp` |
| `examples/02_not_rendered_none_state.py` | rewritten | yes | click (ipyleaflet), box-select (bokeh), brush-drag (altair), page load (k3d auto-fit) | all four: `camera()` not-ready->populated, `clicked()` None->value, `selected()` []->[1,3,4,6,8], `selected()`/`selected_rows()` empty->populated (altair) | yes, both |
| `examples/03_refire_and_clearing.py` | extended (added `double_clicked()` card) | yes | click same marker x2, click different marker, dblclick marker, dblclick background x2 | `clicked()` fires: 2(baseline+1)->2(dedup)->3->5->6->6(dedup); `double_clicked()` fires: 1(baseline)->1->1->2->3->4 | yes, all four |
| `examples/04_rate_limiting.py` | revised (k3d replaces ipydatagrid) | yes | slow box-drag x2 (plotly), slow orbit-drag x2 (k3d) | plotly: 3 vs. 8 fires; k3d: 7 vs. 7 fires (identical regardless of `rate_delay`) | yes |
| `examples/05_rows_of_data.py` | unedited | not re-run (no new claim) | -- | -- | reused existing `05_rows_of_data_after.webp` |
| `examples/06_writing_back.py` | unedited | not re-run (no new claim) | -- | -- | reused existing `06_writing_back_after.webp` |
| `examples/07_lifetimes.py` + `examples/globals.py` | unedited | not re-run (no new claim; the `shared_lifetime()` API itself didn't change) | -- | -- | reused existing screenshots |
| `examples/08_across_rerenders.py` | new | yes | click, zoom-in x2, pan, then click "Re-render" | `clicked()` identical before/after; `zoom()`/`center()` reset from (11.0, panned) to (9.0, [45.5,-122.6]) | yes, both |
| `examples/09_read_on_demand.py` | new | yes | box-select, THEN click "Show selection" | 31 rows shown on first click of a button that had never run before -- the pre-click selection wasn't lost | yes, both |
| `examples/10_read_method.py` | new | yes | zoom-in x2 | `read("zoom")` == `11.0` (matches the accessor); `read("scroll_wheel_zoom")` == `True` (bare trait); `read("zooom")` raised with "Did you mean 'zoom'?" | yes |

Every gesture above was a real Playwright mouse event (`click`, `dblclick`, `mouse.move/down/up` drags) or a
real click on a rendered control (leaflet zoom buttons, a Shiny action button); none used a JS-level trait
assignment. k3d drives used `--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist` per
the brief.

### Old "Bugs found" items, now fixed

- `render_reactable`'s `_accessor_specs` typo (missing leading underscore), reported in the prior pass, is
  fixed on current `main` -- confirmed by reading `shinywidgets/_render_widget.py` directly (only the
  correctly-named assignment remains) rather than re-triggering the five accessors live (the renders already
  work across every other reactable Playwright suite on this commit).

### New bugs or surprises found this pass

None in shinywidgets itself. One authoring trap worth recording here (not a shinywidgets bug): a
`@reactive.effect` that unconditionally reads an accessor and bumps a counter runs once at session start
(standard Shiny effect behavior) *before* any gesture, so the displayed "fires so far" count in
`examples/03_refire_and_clearing.py` starts at 1, not 0, for both cards. This isn't a bug -- the counter is
counting real reactive invalidations, and the effect's own first run is one -- but it's easy to misread as a
double-fire on the very first click when driving the app with Playwright and printing counts step by step;
documented here so a future pass doesn't rediscover it as a false "clicking once fires twice" finding. The
article text reports only relative deltas (never the raw baseline-inclusive numbers) for exactly this reason.

### Judgment calls

- Chose k3d's `camera()` over other still-no-default accessors (e.g. ipyaladin's `target()`/`fov()`) as the
  "no policy" contrast in "Rate limiting" because it reuses a widget already verified elsewhere in this
  article (the `k3d_accessors` Playwright test's own orbit-drag driving pattern), and because its upstream
  ~200ms self-throttle is itself a useful thing to show readers (the renderer's `rate_delay` kwarg is a
  no-op for it in *both* directions -- not even k3d's own throttle is shinywidgets' to control). A second
  opinion on whether ipyaladin (sky pan/zoom) would make a more varied cross-widget selection is reasonable,
  but ipyaladin needs network tile access and is less certain to automate cleanly headless.
- Kept the "kept vs. re-seeded" caveat in "Across re-renders" (ID-keyed lookups) as a citation of the
  relevant docstrings rather than a second live repro showing an actual stale-index mismatch. Building a
  convincing stale-index demo needs a widget whose render function swaps in genuinely different data between
  renders, which would have meant a new, more complex example purely to restate a fact the docstrings already
  state precisely; the maintainer may want a dedicated repro here if the website wants to show the failure
  mode rather than just describe it.
- Classified every accessor's cheat-sheet "Across re-render" column from source (reading each `attach_*`
  function) rather than by exhaustively re-verifying each one in a browser across all ~30 renderers, which
  the time budget for one article didn't allow. This mirrors how the original cheat sheet was built ("Kind"
  and "Default rate" columns were already sourced from `AccessorSpec`, not from browser runs, per the
  original NOTES.md); only the behaviors demonstrated in this article's own examples got full browser
  verification. Flagging this explicitly in case the coordinator wants a dedicated verification pass across
  the full cheat sheet.

## Update 2026-11-11 (Task 5: "Writing back" and "Lifetimes" moved to Updating in place)

Per the site design doc, this article is being trimmed: "Writing back" and "Lifetimes" (with their examples,
screenshots, and the sibling `globals.py`) moved to a new article, `articles/updating-in-place/`. Full
provenance and re-verification of the moved content is in that article's own `NOTES.md`; this entry covers
only what changed in *this* article.

- Both sections replaced with 2-3 line pointers to `../updating-in-place/article.md#writing-back` and
  `#lifetimes`. No content was deleted outright -- it was moved, not cut.
- Fixed the two in-text, non-link references to "Writing back" that would otherwise now dangle: the
  `[Writing back](#writing-back)` link in "Re-firing and clearing" (now
  `[Writing back](../updating-in-place/article.md#writing-back)`) and the plain-text `see "Writing back" for
  why that matters` comment inside `examples/03_refire_and_clearing.py`'s own source (both the markdown copy
  and the actual `.py` file were updated identically, so `check_docs.py --snippets` still passes -- the comment
  now reads `see "Writing back" in the Updating in place article for why that matters`).
- Checked the cheat sheet (`cheatsheet.md`) for any reference to the old `#writing-back`/`#lifetimes` anchors
  or the moved example filenames: none found (`grep -n "writing-back\|Writing back\|Lifetimes\|07_lifetimes\|06_writing_back" cheatsheet.md`
  returned nothing), so it needed no edits.
- Updated the front-matter `summary` (no longer claims "writing back without looping, and the three widget
  lifetimes" as this article's own content) and added an "Updating in place" bullet to "Where to go next".
- `widgets:` front matter and the rest of the article's examples (`01` through `05`, `08` through `10`) are
  unchanged -- the moved sections were self-contained (only `globals.py` was a shared dependency, and only
  `07_lifetimes.py` imported it, confirmed before moving).
- Ran `check_docs.py` on this directory after the trim: clean (no problems beyond `tools/BASELINE.txt`, which
  already had none for this directory).

### Handoff

This article's own inbound links from *other* articles/guides to the old `#writing-back`/`#lifetimes` anchors
(e.g. `articles/linked-views/article.md`, `articles/ai-exploration/article.md`, `articles/performance/article.md`,
`render-widget/guide.md`) are outside this task's owned paths and are recorded as rows in
`docs/widget-guides/tools/handoff/task-5.md` instead of edited here.

## Update 2026-11-11 (kept-accessor loop fix follow-through)

- `article.md` "Across re-renders": removed the now-false claim that a re-render always invalidates accessor
  readers ("even a kept accessor's readers re-run on a re-render"). With PR #457, readers re-run only when
  the accessor's value actually changes (same as ordinary inputs), which the new text states -- and calls out
  that it makes the "click -> derive -> draw on the same plot" pattern safe.
