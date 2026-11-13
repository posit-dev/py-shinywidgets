# NOTES: Datashader guide

## Versions used

- Date: 2026-11-02.
- shinywidgets: worktree detached at `origin/main`, commit `00f90249` ("fix(plotly): bind accessor events...").
- shiny 1.9.0, holoviews 1.23.2, hvplot 0.12.2, datashader 0.19.1, panel 1.10.0, bokeh 3.10.1, jupyter_bokeh
  4.1.0, numba 0.68.1, pandas 3.1.0, numpy 2.5.4 (all already present in the shared worktree venv; no `--with`
  overlays were needed for this guide).
- `render_holoviews` has no `_accessor_specs` (confirmed by reading `shinywidgets/_render_widget.py`), consistent
  with the HoloViews guide's finding. There is no dedicated Datashader renderer or accessor set; Datashader plots
  are plain HoloViews/hvPlot objects rendered through `render_holoviews`.
- Datashader is in the `test`/`dev` dependency groups but not in the `shinywidgets[holoviews]` extra (matches the
  HoloViews guide's note) -- the guide's Installation section tells users to add `datashader hvplot` themselves.

## Verification table

| File | Ran? | Screenshot? | Gesture driven? | Notes |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes (also hero) | n/a (static) | 1,000,000 points |
| examples/02_rasterize_vs_datashade.py | yes | yes | n/a (static) | 500,000 points |
| examples/03_aggregators.py | yes | yes | n/a (static) | count/mean/count_cat, 500,000 points |
| examples/04_dynspread.py | yes | yes | n/a (static, xlim/ylim pre-zoomed) | before/after dynspread, dramatic difference confirmed |
| examples/05_lines_at_scale.py | yes | yes | n/a (static) | 5 x 200,000 = 1,000,000 samples |
| examples/06_zoom_stats.py | yes | yes, before/after | yes: real `page.mouse.wheel()` zoom, 1,000,000 points | 0 console errors; stat dropped from 1,000,000 to 181,938 in view |
| examples/07_boxselect_stats.py | yes | yes, before/after | yes: real drag (`mouse.down/move/up`), 500,000 points | stat: 104,516 of 500,000 rows, mean fare $11.99; `selectiongeometry` event confirmed over the websocket |
| examples/08_filter_aggregator_inplace.py | yes | yes, 3-step sequence | yes: real wheel-zoom + radio-button click + selectize item removal | zoom preserved across both an aggregator switch and a category-filter change |
| gallery/template_zoom_reaggregate.py | yes | yes, before/after | yes: real wheel-zoom | 1,000,000 -> 180,328 in view |
| gallery/showcase_nyc_pickups_explorer.py | yes | yes, 3-step sequence | yes: real box-select drag + wheel-zoom + radio click | 0 console errors; box-select stat (283,496 rows, mean fare $12.00) and zoom-preserving aggregator switch both verified in one session |

No accessors exist on this renderer (inherited from `render_holoviews`), so there's nothing to verify in the
accessor sense; every interactive claim above is instead verified against either the server-side `reactive.Value`
(06, 07, 08) or a direct websocket/console-log check (re-aggregation, box-select wiring).

Payload/latency measurements (separate from the example apps; methodology and full numbers in `guide.md`'s
"Payload and latency at scale" section): a small standalone `measure_app.py` (not shipped in `examples/`, kept
only in scratch) toggled between a plain scatter and `rasterize=True` at N=100,000/1,000,000/10,000,000, with a
Playwright script capturing real websocket frame sizes and wall-clock time to first rendered pixels. The
10,000,000-point measurements (payload, zoom-burst payload, and zoom latency) were each run exactly once, alone,
per the coordinator's resource-constraint instruction after the session crash; all other measurements (100k/1M)
were run normally.

## Bugs found (shinywidgets / upstream / docs / authoring hazards)

1. **[authoring hazard, not a bug, HIGH time-cost while verifying] `hv.streams.BoundsXY` subscribers must name
   their parameter `bounds`.** `BoundsXY` invokes subscribers with the keyword `bounds=...`. A subscriber with a
   differently-named parameter (I first wrote `lambda bounds_val: ...` and separately `lambda b: ...`) raises
   `TypeError: <lambda>() got an unexpected keyword argument 'bounds'` -- but only inside HoloViews' own detached
   `asyncio.create_task`, so it surfaces as "Task exception was never retrieved" in the **server log only**, with
   no browser console error, no exception in the app's own code, and no visible symptom beyond "the box-select
   silently does nothing." I spent real time on this: confirmed the gesture itself was fine (the
   `selectiongeometry` bokeh event was sent correctly over the websocket, with `"final": true` and the right
   `x0/y0/x1/y1`) before finding the actual cause in the server log. Documented prominently in the guide's
   Gotchas section and the box-select example's prose, since the HoloViews guide's own working example already
   gets this right (parameter named `bounds`) but doesn't call out *why* the name matters -- worth a cross-link
   or an explicit callout there too.
2. **[my own test-harness mistake, not a product issue] A box-select drag that starts too close to the y-axis
   margin can land outside Bokeh's `CartesianFrame` hit-test area and silently not initiate a selection.** Found
   while debugging #1: a drag starting at 10% of the canvas width (only ~5px inside the actual plot frame, given
   a roughly 50px y-axis margin) produced no `selectiongeometry` event at all, while the identical code with a
   drag starting at 15-20% worked every time. Not a bug to report -- just a methodology note for future agents
   driving Bokeh box-select gestures with Playwright: start comfortably inside the frame, not near its edge.
3. **[not reproduced here, already investigated] The RangeXY infinite-loop bug (HoloViews guide's Bug #4) does
   NOT affect `rasterize()`'s/`datashade()`'s own internal `RangeXY` stream.** This was the central open question
   this guide was asked to resolve. Verified two ways: (a) the repo's existing
   `tests/playwright/render_holoviews_datashader/test_render_holoviews_datashader.py` passes outright (`2 passed`)
   and drives exactly this path with real gestures; (b) this guide's own `examples/06_zoom_stats.py` additionally
   *subscribes a second callback* to the operation's existing `RangeXY` stream (reading the current viewport into
   a `reactive.Value`) and ran clean at 1,000,000 points with zero console/server errors, zero re-render loop,
   over a sustained 8-tick wheel-zoom gesture. The distinguishing factor (confirmed against
   `../holoviews/INVESTIGATION.md`, which landed mid-task): the loop needs a *newly-constructed*
   `hv.streams.RangeXY(source=...)` whose subscriber writes an ever-changing value (a counter); grabbing the
   *existing* stream object via `next(s for s in img.streams if isinstance(s, RangeXY))` and writing an
   idempotent value (the range tuple itself) avoids it, and `rasterize()`'s own internal re-aggregation logic
   doesn't go through a Shiny `reactive.Value` write at all -- it drives the Bokeh model directly. No
   shinywidgets or holoviews code change indicated; this guide documents the safe pattern.
4. **[docs opportunity, low] `render_holoviews`'s docstring already mentions Datashader re-aggregation and the
   per-session build requirement (in `shinywidgets/_render_widget.py`), and it's accurate** -- no correction
   needed. It does not mention the `RangeXY`-must-be-idempotent nuance from item 3, since that's specific to a
   *user* adding their own subscriber on top of the existing stream, not a general Datashader concern; I judged
   this belongs in this guide's prose (where the full context is established) rather than as a docstring
   addition.

## Judgment calls for the maintainer to revisit

- **No real/downloaded dataset was used.** I considered the datashader/holoviz community's classic NYC taxi
  dataset (an 11M-row public parquet), but decided against downloading it given the brief's "small, stable public
  URLs" guidance and the operating rules' resource constraints (machine load, serial-only execution after the
  mid-task crash). Instead I used a synthetic dataset explicitly positioned at real NYC landmark coordinates
  (Times Square, Wall Street, JFK, LaGuardia, Central Park, etc.) with a plausible Gaussian spread per landmark --
  clearly labeled as synthetic in both the guide prose and every example's comment header. This mirrors the
  precedent set by `jscatter/examples/02_scale.py` (cluster-based synthetic data) elsewhere in this roster. A
  maintainer who wants a real public dataset for the website version could swap in a small real NYC/census
  extract without changing any of the plotting code.
- **The showcase gallery app keeps the aggregator choice to "count" vs "mean fare" only**, skipping an
  interactive `count_cat` toggle. Switching between `rasterize()` and `datashade()` (needed for `count_cat`'s
  categorical color blending) isn't a simple param-ref swap the way switching aggregators within one operation
  is -- it would need swapping the whole operation pipeline reactively, which felt like a separate, riskier
  pattern to verify under the time/resource budget, especially after the mid-task crash. `count_cat` is still
  fully covered as a static example (`03_aggregators.py`). Flagging in case a future pass wants an interactive
  categorical-aggregator showcase.
- **The payload/latency table's "time to first pixels" numbers are this-machine, this-session numbers under
  variable background load** (the operating environment explicitly notes the machine is shared with ~10 other
  agents, and one crash from overload happened mid-task). I treated the *relative* comparisons (flat rasterize
  payload vs linear plain-scatter payload; sub-second zoom re-aggregation) as the reliable finding, consistent
  with the old report's own methodology note ("relative comparisons held up across runs"), rather than treating
  the absolute wall-clock seconds as precise.
- **Session/shared-data guidance explicitly corrects a possible misreading of the assignment brief.** The brief
  suggested "`shared_lifetime` / `globals.py` for the big frame" as the pattern to document. I verified
  (`shared_lifetime()`'s own docstring, read directly in `shinywidgets/_shinywidgets.py`) that `shared_lifetime()`
  is for sharing one ipywidget *instance* across sessions -- exactly the behavior that leaks one user's zoom to
  everyone else, which both this guide and the HoloViews guide warn against for a Datashader `DynamicMap`. The
  globals.py idea is still right, but for a different reason than "use shared_lifetime": it's about avoiding
  Shiny Express's per-session top-level re-execution for the *plain dataframe*, not about using shinywidgets'
  shared-widget machinery. I verified the per-session re-execution behavior directly (a persistent counter in a
  helper module incremented once per new browser session, not once at process start) rather than assuming the
  brief's framing was accurate. Flagging this clearly in case the brief's phrasing was based on a different
  mental model than what I found in the code.

## Editor's notes for the website

- Strongest sections: the payload/latency table (flat Datashader payload vs linear plain-scatter payload, plain
  scatter failing to even finish at 10M) and the re-aggregation-on-zoom verification (directly answers the
  highest-priority open question in this assignment) are the most load-bearing content in the guide. If trimming
  for a shorter page, keep both in full.
- The dynspread before/after (`04_dynspread.webp`) is the most immediately legible screenshot -- completely empty
  vs. visibly dotted, no need to read axis labels to get the point.
- Candidate for trimming: the "Lines and time series at scale" subsection is good but could compress to a single
  paragraph + screenshot if space is tight; it's the least differentiated section relative to the point-based
  examples (same `count_cat`/`color_key` recipe, different element type).
- The "Session and shared-data memory notes" section is denser prose than the rest of the guide (no code snippet
  of its own). Consider whether the website wants a short code example of the "data.py + Express app.py" split
  pattern; I left it as prose since the pattern itself (a plain Python import) isn't Datashader-specific enough
  to warrant its own runnable example file, and no other guide in the roster ships one either.

## What I dropped from the old report and why

- "Cross-session leak (module-level DynamicMap)" -- kept, reframed per the HoloViews guide's phrasing (covered
  there in more depth; this guide cross-references rather than re-deriving it).
- "Aggregation runs on Shiny's event loop, blocking other sessions" -- kept as a brief Gotcha, but softened: my
  own measurements found Datashader's Numba kernels fast enough (well under 100 ms even at 10M points on this
  machine) that this is rarely the practical bottleneck, matching the old report's own finding, so I didn't
  belabor it.
- "Retained widgets / BokehModel leak per re-render" (shinywidgets bug, pre-existing) -- not re-verified in this
  pass (out of scope: it's a general `render_holoviews`/re-render lifecycle question, not specific to
  Datashader, and the HoloViews guide's own Gotchas section doesn't currently list it either; if it's still
  present it belongs there, not duplicated here).
- "On released shiny (1.8.0), the image is always one gesture behind" -- dropped entirely; shiny's floor is
  `>=1.9.0` in `pyproject.toml` now, so this no longer applies to any supported configuration.
- "`[tool.uv.sources]` pins shiny to git main" / PR-merge-readiness discussion -- dropped; this guide documents
  the shipped feature on current `main`, not a historical PR review.
- "Pixel_ratio=None can't detect DPR outside panel server/notebook" / Retina rendering at 1x -- dropped as a
  gotcha (not re-verified); worth a future pass if HiDPI screenshots matter for the website.
- "Extra re-aggregations when axis tick labels change width (PlotSize churn)" -- dropped as a dedicated item; did
  not specifically re-measure it, and it felt like upstream-HoloViews trivia relative to the higher-value findings
  above, consistent with the brief's "report bugs found, not hypothetical issues" and "weigh value against
  complexity" guidance -- a user is unlikely to notice or care about one extra re-aggregation pass.
- Kept, newly verified rather than carried forward unverified: the "image payload is flat regardless of N" and
  "re-aggregation latency" claims -- the old report had its own numbers (from an unreleased shiny dev build); I
  re-measured from scratch on released shiny 1.9.0 rather than reuse old numbers that predate today's dependency
  versions.

## Update 2026-11-11 (main @ 32ca7035)

- shinywidgets commit: `main` @ `32ca7035` (worktree `main-wt`). Same library versions as the prior pass
  (datashader, holoviews 1.23.2, hvplot 0.12.2, panel 1.10.0, bokeh 3.10.1, jupyter_bokeh 4.1.0), Python 3.13.17.
- **Fixed stale `RangeXY`-loop framing left over from before the HoloViews guide's own correction** (same issue
  as the GeoViews guide had): the "Re-aggregation on zoom" intro, the "Takeaway" paragraph, the
  `examples/06_zoom_stats.py` code comment, the "needs a specific warning" paragraph, and a Gotchas entry all
  described the construct-your-own-`RangeXY` case as something that "showed the infinite-loop bug" -- true before
  #411, not true now. Rewrote all five to credit the fix (`reactive.isolate()` around widget coercion; see the
  HoloViews guide's Gotchas for the mechanism) and reframe "grab the existing stream, don't build a second one"
  as what it now is: avoiding a redundant stream, not avoiding a crash. No code changed in `examples/06_zoom_stats.py`
  or `examples/07_boxselect_stats.py`, only prose and one code comment.
- **Did not independently re-verify** whether a second, independently-constructed `RangeXY(source=img)` on a
  rasterized element works correctly (vs. just not crashing) post-fix -- out of scope for this pass, since the
  guide's recommendation (reuse `rasterize()`'s own stream) doesn't depend on the answer either way. Flagging in
  case a future pass wants to confirm it works, not just that it doesn't loop.
- The general #411 fix was re-verified directly (not assumed) via the shared HoloViews-guide repro
  (`../holoviews/repros/rangexy_render_loop_repro.py`, a counter-style `RangeXY` subscriber): 0
  `RuntimeError: BokehModel was closed` on current main, versus 432+ before the fix. The fix lives in
  `render_widget_base._render()`, which every `@render_holoviews` render goes through regardless of
  datashader/rasterize involvement, so this one repro covers the mechanism for this guide too; didn't additionally
  re-run `examples/06_zoom_stats.py`/`07_boxselect_stats.py` live this pass since their code is unchanged and
  their original verification (real scroll-zoom/box-select gestures, documented above) already covers them.
- **Confirmed `param(name)` does not reach `render_holoviews`** (same check as the HoloViews and GeoViews guides):
  no `param()` method, no `_dynamic_accessor_spec()` override. Not mentioned in this guide; nothing needed adding.
- No dedicated `reactive_read()`/`.read()` subsection exists in this guide (it defers to the HoloViews guide's
  Gotchas cross-reference for everything not specific to Datashader) -- left as-is, since adding one would just
  duplicate the HoloViews guide's now-updated note rather than add Datashader-specific information.
- No other PR in 00f90249..32ca7035 touches anything this guide documents (checked `shinywidgets/_as_widget.py`
  and the `render_holoviews` class directly).

### Bugs found (2026-11-11)

None newly found; no previously-reported items in this guide were affected by anything in 00f90249..32ca7035.

## Pairs with

- [holoviews](../holoviews/index.md) -- the rendering mechanism and full stream/`link_selections` model (direct
  prerequisite, linked throughout).
- [geoviews](../geoviews/index.md) -- for geospatial map tiles/projections alongside Datashader rasterization
  (not duplicated here per the coordinator's instruction; geoviews guide was still being written in parallel).
- [jscatter](../jscatter/index.md), [lonboard](../lonboard/index.md), [embedding-atlas](../embedding-atlas/index.md),
  [perspective](../perspective/index.md) -- big-data alternatives, compared and linked in "Learn more."

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views" (before the pre-existing "Payload and latency at scale" section, which it now introduces and links to by anchor rather than duplicating). Also applied Task 6's handoff row (cross-link to the linked-views article's new brushing-at-scale pattern) as the section's closing paragraph, verbatim; marked applied in `tools/handoff/task-6.md`.
