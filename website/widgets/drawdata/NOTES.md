# NOTES: drawdata guide

## Versions and environment

- Date: 2026-11-02.
- shinywidgets: `main` @ `00f90249` (the assigned worktree `/private/tmp/claude-502/.../scratchpad/main-wt`,
  detached at `origin/main`).
- drawdata 0.5.2, shiny 1.9.0, plotly 6.9.0, altair 6.3.0, matplotlib 3.11.2, numpy 2.5.4, pandas 3.1.0, polars
  2.0.0. scikit-learn is not in the shared worktree venv; examples/gallery apps that need it say so in a header
  comment and were run with `uv run --no-sync --with scikit-learn python -m shiny run ...` (per the coordinator's
  note: use `python -m shiny run`, not the `shiny` console script, so the `--with` overlay actually applies).
- Ports used: 9800-9811 (within the assigned 9800-9819 range). Scratch driver scripts and a shared
  `helpers.py` (fraction-of-bounding-box drag helper) live in
  `/private/tmp/claude-502/.../scratchpad/agents/drawdata/`.
- **drawdata has no reactive accessor methods** (`render_drawdata` is a direct `render_widget_base` subclass with
  no `_accessor_specs` override, confirmed by reading `shinywidgets/_render_widget.py`), so "accessor coverage"
  doesn't apply -- every example uses the `reactive_read()` tier instead.

## Verification table

Every example and gallery app ran via `uv run --no-sync shiny run` (or `--with scikit-learn python -m shiny run`
for the three that need it), driven with Playwright (headless Chromium, 1280x800 or 1280x500,
`device_scale_factor=2`), and every screenshot was viewed with the Read tool before being referenced in
`guide.md`.

| file | ran | screenshot(s) | gesture driven | notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | `01_quickstart_before/after.webp` | real 2-stroke drag (different classes) | point count confirmed |
| `examples/02_live_dataframe.py` | yes | `02_live_dataframe_before/after.webp` | real drag, 2 classes | table rows match drawn points, including `label`/`color` |
| `examples/03_bar_sculpting.py` | yes | `03_bar_sculpting_before/after.webp` | 16 real bar drags (bell shape) | summary stats match; confirmed single `collection_names` hides the switcher/Clear buttons |
| `examples/04_reading_drawn_data.py` | yes | `04_reading_drawn_data_before.webp`, `_after_stroke1.webp`, `_after.webp` | 2 real strokes | **directly demonstrates the one-batch lag**: 10 points on screen, "0 points synced" after stroke 1; 20/both batches after stroke 2 |
| `examples/05_rate_limiting.py` | yes | `05_rate_limiting_during/after.webp` | one continuous real bar drag (~40 pointer moves) | unthrottled: 43 reads; throttled (`rate_delay=1`): 4 reads during the drag, 5 after settling |
| `examples/06_clear_and_reset.py` | yes | `06_clear_and_reset_before/after.webp` | real strokes + bar drags, then both buttons clicked | scatter cleared in place (circles removed from DOM); bar reset via re-render; both counts went to 0 |
| `examples/07_classifier_boundary.py` | yes | `07_classifier_boundary_before/after.webp` | 4 real strokes, alternating classes | boundary visibly separates the two colors; `scaleanchor="x"` confirmed matching aspect ratio |
| `examples/08_regression_fit.py` | yes | `08_regression_fit_before/after.webp` | 3 real strokes (single class) | quadratic curve follows the drawn trend; `data_as_X_y` regression-mode branch exercised |
| `examples/09_compare_distributions.py` | yes | `09_compare_distributions_before/after.webp` | real bar drags in both collections, switched via the `collection2` button | altair overlay matches both sculpted shapes exactly |
| `examples/10_clustering.py` | yes | `10_clustering_before/after.webp` | 3 real strokes (3 separated blobs), single class | k-means (k=3, default slider) colors the three blobs correctly |
| `gallery/template_classifier_playground.py` | yes | `gallery_template_classifier_playground_before/after.webp` | 4 real strokes | clean separation; used as the guide's hero image |
| `gallery/showcase_model_explorer.py` | yes | `gallery_showcase_model_explorer_classify_after.webp`, `_regress.webp`, `_cluster.webp` | real strokes in all 3 modes, radio-button task switches | all three tasks verified working from one app; confirmed task switch clears/re-renders the canvas with the right `n_classes` |

No gesture in this guide needed a fallback (no WebGL/WebGPU, no un-drivable pixel-picking) -- drawdata's canvas
is plain SVG with ordinary `mousedown`/`mousemove`/`mouseup`, which Playwright drives directly.

### A real debugging detour worth recording

Early screenshot attempts for `08_regression_fit.py` used hardcoded pixel offsets (e.g. "drag from (60, 300) to
(276, 274)") sized for the widget's nominal 800x400 data space. In a two-column layout the chart is displayed
scaled down (e.g. measured 562x281px for an 800x400 widget), so a `y0=300` offset landed *below* the actual
rendered `<svg>` -- outside its bounding box -- and the resulting drag silently drew nothing (0 circles added).
This looked exactly like a product bug (a stroke "disappearing") until bisection (same stroke, different
starting position) isolated it to my own test script. Fixed by switching every driver to fractions of the
*current* `bounding_box()` of the chart element (see `scratchpad/agents/drawdata/helpers.py`), which is robust to
whatever scaling the layout applies. Recorded here so the next person debugging a "stroke didn't register"
report checks this before assuming a drawdata regression.

## Bugs found

All of the following are **upstream drawdata bugs/limitations**, not shinywidgets regressions. `render_drawdata`
already documents each one in its docstring, and I independently re-verified every claim in a real browser (or,
for the two purely static-code claims, by reading the installed `scatter_widget.js`/`bar_widget.js` bundles,
since they're unconditional -- no gesture could make them not true).

1. **`ScatterWidget`'s first drawing batch doesn't sync to Python until a second batch starts drawing**
   (drawdata's frontend mutates its points array in place, so the sync's deep-equality check sees "no change" on
   the first batch). Re-verified directly: `examples/04_reading_drawn_data.py` shows "0 points synced" after a
   10-point stroke, then "20 points synced, across batches [0, 1]" after a second stroke. Long-standing upstream
   limitation (also documented by the earlier spike report in `docs/widget-reports/drawdata/report.md`), not a
   shinywidgets regression.
2. **`BarWidget` overwrites constructor-provided `data` at first render and ignores all Python-side trait writes
   afterward** -- confirmed by reading `bar_widget.js`'s `render()` (it rebuilds `collections` from scratch,
   never reading `model.get("data")`) and by grepping for `model.on("change:` in that bundle, which matches
   nothing. Treat a rendered `BarWidget` as browser-driven only; re-render to change anything.
3. **`BarWidget`'s default `collection_names` is `["collection1", "collection2"]`**, not a single plain
   distribution. This surprised me initially (I expected an empty single histogram); it's `drawdata`'s own
   default, not something shinywidgets changes. Worth calling out explicitly in the guide since it changes what
   the widget looks like out of the box.
4. **`data_as_X_y` reports hex color codes as `y` for the classification case**, not the `"a"`/`"b"`/`"c"`/`"d"`
   labels (confirmed: constructed a 2-point dataset and printed `data_as_X_y`, got back hex strings). Also
   documented in the older spike report. Not currently mentioned in the `render_drawdata` docstring -- a possible
   small addition for shinywidgets maintainers, but it's a pure upstream-library quirk, so I only documented it
   in the guide rather than flagging it as a shinywidgets bug.
5. **One harmless console error per `ScatterWidget` render**: `<svg> attribute height: Expected length, "auto"`.
   Cosmetic; matches the existing `tests/playwright/render_drawdata/test_render_drawdata.py` allowed-errors list.

No shinywidgets-side regressions found. The one shinywidgets-side behavior worth knowing (not a bug, a
deliberate fix) is the layout one below.

## Judgment calls

- **Picked k-NN for the classifier pattern, logistic regression as a secondary note in the showcase.** k-NN's
  boundary is visually more responsive to a hand-drawn, non-linear-looking split, which reads better in a
  screenshot; logistic regression's accuracy score is a nice one-line stat for the showcase sidebar. Either is a
  reasonable default -- flagging in case the maintainer prefers consistency with another guide's choice of
  classifier for cross-guide comparison purposes.
- **Used `BarWidget`'s re-render-to-reset pattern for the showcase's "Clear canvas" button on the `ScatterWidget`
  too** (rather than mixing the in-place `widget.data = []` approach from `06_clear_and_reset.py`), because the
  showcase already re-renders the canvas on every task switch (to change `n_classes`) and using one mechanism
  uniformly seemed clearer than mixing both in the same app. The dedicated `06_clear_and_reset.py` example in the
  guide body does show both mechanisms side by side, which I think is the right place for that contrast.
  Revisit if the maintainer would rather the showcase demonstrate the in-place path explicitly too.
- **Didn't give drawdata its own dedicated "Rate limiting" example using `ScatterWidget`.** Scatter's own batching
  (one sync per stroke, already naturally coarse) doesn't give `rate_policy` much to do, so I used `BarWidget`
  (which syncs on every pointer move) instead, matching the reasoning the ipysigma guide used for the same
  choice. Mentioned explicitly in the guide text.
- **Did not assign drawdata an "issue number" for the `data_as_X_y` hex-color quirk** (unlike the one-batch-lag
  and BarWidget-overwrite quirks, which `render_drawdata`'s own docstring already cites by number, so I treated
  those as safe to repeat). Per the operating rules, I didn't browse drawdata's GitHub issue tracker to find or
  verify a current issue number for this one, so I described the behavior without citing one.
- **Gallery showcase scope**: kept to 3 tasks (classify/regress/cluster) in one app rather than also including
  the bar-sculpting or distribution-comparison patterns, to stay under the "showcase" bucket's complexity target.
  Those two have their own dedicated examples (03, 09) instead.

## Editor's notes for the website

- **Strongest visual**: `gallery_template_classifier_playground_after.webp` (used as the guide's hero) -- clean
  two-class separation, a visible k-NN boundary, a neighbor slider, and a point counter all in one clean
  screenshot. The showcase's three-mode screenshots are a good second set if the page wants more than one image
  above the fold.
- **What to cut for a shorter page**: the "What you can build" section (live dataframe, bar sculpting) could be
  trimmed to just the classifier-boundary highlight if the page needs to be shorter -- the two gallery apps
  already cover the dataframe/sculpting mechanics implicitly.
- The "Reacting to user interaction" section's one-batch-lag subsection is, I think, the most important single
  paragraph in the guide for a new user -- it is the first thing anyone will trip over. Consider pulling it (or
  a condensed version) above "What you can build" if the final page allows reordering, since right now a reader
  only reaches it after several other sections.
- The showcase's radio-button task switcher is a nice demonstration of "re-render on a UI control, not just a
  button," which none of the other examples show; worth keeping if the page trims gallery apps down to one.

## Dropped from the old report (`docs/widget-reports/drawdata/report.md`)

- Its entire "PR review" section (about the original spike's own commit, `drawdata_layout_defaults`, test
  additions) -- stale implementation history, not useful to a guide reader, and the renderer has since evolved
  (the real fix now lives in `js/src/fill.ts`'s `relaxDrawdataSize`, not a Python-side layout-defaults function).
- The "0.52 MB inline ESM per render" bundle-size note -- true but generic (every anywidget-based renderer ships
  its bundle inline); the roster already has cross-cutting coverage of this theme per the brief, so I left it out
  of a per-widget guide.
- The "two ScatterWidgets on one page" red-herring discussion -- confirmed not an issue; not worth repeating even
  as a "non-issue," so I dropped it rather than explaining a bug that doesn't exist.
- Its scorecard table and "magic" bullet list -- format doesn't fit this guide's skeleton; their content is
  folded into the intro paragraph and "What you can build" section instead.
- Kept and re-verified: the one-batch-lag root cause explanation, the `BarWidget` overwrite/no-change-handler
  finding, and the `data_as_X_y` hex-color quirk -- all still true on current `main`.

## Pairs with

- **plotly** -- decision-region contour fills (`07_classifier_boundary.py`, the gallery template).
- **matplotlib** -- quick static fits (`08_regression_fit.py`).
- **altair** -- categorical overlays, grouped/overlaid bars, the showcase's three-task model view
  (`09_compare_distributions.py`, `10_clustering.py`, `gallery/showcase_model_explorer.py`).
- **ipycanvas** -- linked in "Learn more" as the sibling to reach for when the drawing itself needs to be
  free-form (not points/bars).

## Update 2026-11-11 (main @ 32ca7035)

### What changed and why

- Converted every `reactive_read(canvas.widget, "data")` / `reactive_read(hist.widget, "data")` /
  `reactive_read(unthrottled.widget, "data")` / `reactive_read(throttled.widget, "data")` to `canvas.read(...)`
  / `hist.read(...)` / etc. across `guide.md`, 10 example files, and 2 gallery apps -- every read in this guide
  targets the output's own rendered `ScatterWidget`/`BarWidget`, so there was nothing to keep on
  `reactive_read()` for (drawdata has no child widgets). Updated imports (dropped the now-unused `reactive_read`
  import, including the two files that also import `render_altair`) and the on-screen strings in
  `examples/05_rate_limiting.py` (the markdown lead-in and both counters' `render.code` output said
  `reactive_read()`; now say `.read()`) -- regenerating nothing else, since no other file's on-screen text
  mentioned the call by name.
- Reworded the intro, "Reacting to user interaction", "Rate limiting", "Gotchas", and "Learn more" prose to
  teach `.read("data")` as the primary call, replacing the old framing that pointed at `reactive_read()` and the
  render-widget guide as the only story.
- **New example**, per the brief's suggestion: `examples/11_fit_on_demand.py` and a new "Fit on demand, not on
  every stroke" subsection in "Coordinating multiple views". Variation on the existing classifier-boundary
  pattern (`07_classifier_boundary.py`), but the k-NN refit is gated behind a "Fit model" button
  (`@reactive.event(input.fit)`) instead of running on every synced stroke. Demonstrates that a synced trait
  already holds whatever was drawn before the click -- not a *new* capability for a bare trait (unlike an
  accessor, a plain ipywidgets trait was never subject to the old "attaches on first read" problem), but a
  genuinely useful pattern worth teaching here: an expensive fit shouldn't re-run on every pointer move.

### Verification

- `examples/11_fit_on_demand.py` (new): ran in browser (`uv run --no-sync --with scikit-learn`, matching this
  guide's existing `--with scikit-learn` convention for the classifier example). Drew two strokes of class `a`
  and two of class `b` (avoiding the one-batch sync lag) via a real `mousedown`/`mousemove`/`mouseup` drag
  sequence on `svg.dd-scatter-svg`, confirmed the right panel stays completely empty before the click (output
  never ran -- `@reactive.event` with no prior click), then clicked "Fit model" and confirmed the decision
  boundary renders with both clusters correctly separated and colored. Fresh before/after screenshots taken and
  looked at (Read tool).
- `examples/05_rate_limiting.py` (edited, on-screen text changed): re-ran with a continuous bar drag; both
  counters' `.read()`-labeled output confirmed updating as before (throttled counter visibly lagging the
  unthrottled one). Did not re-screenshot `05_rate_limiting_during/after.webp` -- the counts shown are the
  mechanism being demonstrated and would differ run to run regardless of this edit (same as the original pass
  noted), and the only text that changed (`reactive_read()` -> `.read()`) is below the screenshot crop in the
  existing images on closer inspection... actually re-verified by reading the existing screenshots: the
  `render.code` panel *is* visible and *does* show the old `reactive_read() ran N times` string, so both
  screenshots were regenerated. See below.
- `examples/01_quickstart.py`, `02_live_dataframe.py`, `03_bar_sculpting.py`, `04_reading_drawn_data.py`,
  `06_clear_and_reset.py`, `07_classifier_boundary.py`, `08_regression_fit.py`, `09_compare_distributions.py`,
  `10_clustering.py`, `gallery/template_classifier_playground.py`, `gallery/showcase_model_explorer.py` (all
  edited): mechanical conversions, no on-screen text affected (none of these files render the string
  `"reactive_read"` to the UI), so existing screenshots remain accurate and were not regenerated. Not
  independently re-driven with a live gesture this pass; `.read()`'s fallthrough to `reactive_read()` for a bare
  trait is byte-for-byte the same call (confirmed by reading `shinywidgets/_render_widget_base.py`), and every
  one of these traits was already gesture-verified in the 2026-10-30 pass.

### `05_rate_limiting.py` screenshots regenerated

`img/05_rate_limiting_during.webp` and `img/05_rate_limiting_after.webp` both show the `render.code` panel with
the on-screen `.read()`-labeled counter text, so both were regenerated (not left as-is like the other edited
files above, which don't render that string to the UI). Drove the same real bar drag on *both* the unthrottled
and throttled `BarWidget`s (the original pair apparently did too, since both panels show an identical sculpted
shape) and screenshotted mid-drag and after settling. New counts for this pass: unthrottled 34 reads, throttled
5-6 reads for the same gesture -- numbers differ from the original pass's (43 vs. 5), as expected for a
wall-clock-dependent gesture on a shared machine; the qualitative claim (throttled reads far fewer times for
the same drag) holds. The "during" and "after" captures ended up visually similar in this pass (both widgets'
bars were already close to their final shape by the time the mid-drag screenshot was taken) -- a looser
before/after contrast than the original pair, but the counter text underneath still makes the throttling effect
clear (34 vs. 5-6).

### Bugs found (2026-11-11)

None new.

## Update 2026-11-11 (smoke follow-up: 03_bar_sculpting startup race)

- `examples/03_bar_sculpting.py`: the smoke run's server-side `KeyError: 'value'` is a real (timing-dependent)
  startup race, not noise. `BarWidget().data` is `[]` until the browser's first sync, so
  `pd.DataFrame(hist.read("data"))` has no `"value"` column when `summary()` runs early, and `df["value"]`
  raised. Fixed with `drawn = df[df["value"] != 0] if "value" in df else df` (an empty no-column frame reads
  as "No bars raised yet."). guide.md needed no change (it only quotes the `hist()` block). Re-verified in
  Chromium: three bars raised by real drags, summary shows "3 of 20 bins raised / mean 0.92", zero KeyErrors
  in the server log (screenshot looked at).
- The `<svg> attribute height: "auto"` console error did **not** reproduce in this run; the widget sets
  `style="width: 675px; height: auto; aspect-ratio: 800 / 550;"` inline, so the smoke's error was likely the
  SVG's transient pre-layout state. Treating it as noise, as the follow-up suspected.
