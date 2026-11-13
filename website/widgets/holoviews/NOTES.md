# NOTES: HoloViews & hvPlot guide

## Versions used

- Date: 2026-10-30 (initial verification), resumed 2026-11-02 after a session restart (same worktree commit, same
  venv), revised 2026-11-02 again following `INVESTIGATION.md`'s root-cause pass on bugs #1/#2/#4, and revised
  once more (review pass C) following
  `../investigations/narrow-canvas-and-subclass/INVESTIGATION.md`'s retraction of the "narrow panel width breaks
  box-select" finding -- see "Retracted: panel width matters" below.
- shinywidgets: worktree detached at `origin/main` commit `00f90249` ("fix(plotly): bind accessor events...").
- shiny 1.9.0, holoviews 1.23.2, hvplot 0.12.2, panel 1.10.0, bokeh 3.10.1, jupyter_bokeh 4.1.0, plotly 6.9.0.
- Confirmed `shinywidgets[holoviews]` extra = `holoviews, panel, jupyter_bokeh>=4.1` (pyproject.toml). **hvplot,
  datashader, and geoviews are NOT in the extra** -- only in the `test`/`dev` dependency groups. The guide calls
  this out explicitly; users following just the `pip install` line would be missing `hvplot`.
- Confirmed via `shinywidgets/_render_widget.py` and `_accessors.py`: `render_holoviews` has no `_accessor_specs`
  and no accessor methods. Cross-checked against
  `docs/plans/2026-10-29-reactive-accessors-candidates.md` (line ~160, "holoviews | none | ... | Streams must
  exist before the plot is built") and `2026-10-29-reactive-accessors-design.md` ("holoviews and panel get no
  accessors"). This is a deliberate, final design decision, not a gap to fill.
- Also confirmed: the design doc's "open decision" #3 (extending `reactive_read`/`reactive_depend` to
  `param.Parameterized` objects, which would cover holoviews streams and `link_selections` with no accessors at
  all) is **not implemented** on current main -- `reactive_depend()` in `_shinywidgets.py` still requires
  `widget.has_trait(name)` and calls `widget.observe()`, which only works on ipywidgets traits. The guide's
  stream-subscriber recipe is the only verified-working mechanism today.

## Verification table

| File | Ran? | Screenshot? | Gesture driven? | Notes |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes (also hero) | n/a (static) | |
| examples/02_overlays_layouts.py | yes | yes | n/a (static) | |
| examples/03_link_selections.py | yes | yes, before/after | yes: box-select tool clicked, then dragged | |
| examples/04_gapminder_slider.py | yes | yes, before/after | yes: slider handle dragged to max | |
| examples/05_responsive_sizing.py | yes | yes | n/a (static) | |
| examples/06_boxselect_table.py | yes | yes, before/after | yes: box-select drag | table fills from 0 to 29 rows |
| examples/07_update_in_place.py | yes | yes, before/after | yes: wheel-zoom tool inert, switched to box-zoom tool + drag on both plots, then button click | left plot keeps zoomed x-range, right resets |
| examples/08_tap_detail.py | yes | yes, before/after | yes: single click | |
| examples/09_link_selections_dashboard.py | yes | yes, before/after | yes: box-select tool clicked, then dragged | value boxes update (244/244 -> 203/244) |
| examples/10_zoom_range_summary.py | yes | yes, before/after | yes: box-zoom tool clicked, then dragged | 244/244 -> 9/244 visible; 0 `RuntimeError`s across the session |
| gallery/template_crossfilter.py | yes | yes | yes: box-select drag | full-width single card; 200/244 and 165/244 in re-tests |
| gallery/showcase_tips_explorer.py | yes | yes, before/after | yes: box-select drag + tap click | sidebar restored, two outputs restored (see "Retracted findings"); 244/244 -> 195/244, tap detail card populated |

Accessors: none exist on this renderer, so there is nothing to verify "with a real gesture" in the accessor
sense. Every interactive example above instead verifies the stream-subscriber recipe with a real Playwright
gesture (click or drag), confirmed against the server-side reactive value (not just a screenshot) for the cases
(06, 09, 10, and the retests below) where that mattered most.

## Retracted findings (see `INVESTIGATION.md`)

A follow-up root-cause investigation (`docs/widget-guides/holoviews/INVESTIGATION.md`) re-ran my repro files with
real Playwright drags and the server-side `selection_expr`/reactive value as ground truth, and could not
reproduce two of my original four bugs:

- **"`ui.sidebar()` breaks `link_selections` box-select"** -- retracted. 10/10 sessions of my own
  `docs/widget-guides/holoviews/repros/sidebar_breaks_linksel_repro.py` selected correctly with the sidebar in place. I re-verified this myself after
  reading `INVESTIGATION.md`: my original drag box (a wide 20%-80%-of-output region on the right-skewed `tips`
  scatter) excluded almost no points, so "244 of 244 before and after" looked identical to "the callback never
  fired" even though it had fired correctly. A drag that visibly subsets the data (e.g. 20%-45% width, 15%-85%
  height of the actual canvas rect, measured via `getBoundingClientRect()`, not guessed as a fraction of the
  output container) gives a real, changed, repeatable count (162-165 of 244 across 3 trials) with the sidebar
  present. Not a bug.
- **"A second, unrelated `@render_holoviews` output breaks `link_selections` on the first"** -- retracted for the
  same reason, and re-verified myself the same way: with a corrected drag region, box-select on the first output
  correctly selects 137/244 consistently across 3 trials with a second, independent output present. Not a bug.

Both retractions are consistent with a shared root cause in my *own* test methodology (an under-selective drag
region), not a defect in shinywidgets, panel, or holoviews -- see `INVESTIGATION.md` for the detailed
re-verification log. The guide and gallery app have been reverted/updated accordingly: `ui.sidebar()` and a
second `@render_holoviews` output are both back in `gallery/showcase_tips_explorer.py`.

## Retracted: "panel width matters" (superseded by a later investigation)

While restoring the richer showcase layout, I originally reported a **third, seemingly new** issue in the same
family as the two retracted above: **a `link_selections`-wrapped panel narrower than roughly 300px silently stops
registering box-select**, regardless of sidebar or second-output, isolated (I believed) down to panel pixel width
specifically across five width variants.

**Retracted** following
`../investigations/narrow-canvas-and-subclass/INVESTIGATION.md` (Item A). Width was never the real variable: my
repro files (`repros/narrow_panel_breaks_linksel_fullwidth_control.py`, `repros/narrow_panel_breaks_linksel_repro.py`)
never clicked the box-select toolbar icon before dragging. A composite, `link_selections`-wrapped `Layout`
defaults its drag tool to `PanTool`, not `BoxSelectTool`, regardless of width (confirmed directly via Bokeh's own
`Toolbar.active_drag` model) -- so a drag that never switched tools first fails identically at every width,
including the "working" full-width case, which I most likely got to pass by having clicked the toolbar in that
run but not the narrow one (this guide's own sibling examples 03/09 do document clicking the toolbar first,
exactly the step my narrow-panel repro skipped). The real, width-independent fix, verified by the investigation
and now applied throughout this guide and its gallery apps: set `.opts(active_tools=["box_select"])` on each
element before combining them with `links(...)`, so box-select is the default drag tool from the first render.
This is no longer gotcha #1 (see the guide's current Gotchas list); the full row width given to the showcase's
crossfilter card is kept as a layout preference, not a bug workaround.

## Bugs found (shinywidgets / upstream, verified on current main)

Ranked roughly by how likely a user is to hit them. (Numbering restarts here; the two retracted findings above,
plus the retracted "panel width" finding, are no longer counted as bugs.)

1. **[up or sw boundary, MEDIUM-HIGH] `hv.streams.Tap` attached to an element that is also wrapped by
   `hv.link_selections` never fires.** The tap-select tool appears in the toolbar and can be activated, but
   clicking does nothing -- `tap_xy` stays `None` forever. Re-verified in this revision with a careful gesture
   (tap-select tool explicitly activated first, two separate click coordinates tried) and the server-side
   `reactive.Value`, not just a screenshot: both taps left `tap_xy` at `None`. A control app (identical `Tap`
   subscriber, no `link_selections`) correctly reported both taps' `(x, y)` in the same session using the same
   driver script, ruling out a gesture/harness problem. Repro:
   `docs/widget-guides/holoviews/repros/tap_plus_linksel_same_element_repro.py`.
   Worked around throughout the guide (and in the restored showcase) by attaching `Tap` to a separate, unlinked,
   fixed-size plot.
2. **[up, MEDIUM, real mechanism confirmed, docs-only fix] `hv.streams.RangeXY` causes an infinite re-render loop
   if the subscriber writes an ever-changing value.** Per `INVESTIGATION.md`'s root-cause: shinywidgets renders
   every `@render_holoviews` output onto a bare `bokeh.document.Document()` with no session context (necessary
   for its jupyter_bokeh-based architecture, not a real bokeh server), which routes HoloViews'
   `Callback._schedule_event` down the "detached `asyncio.create_task()`" branch for every stream callback, not
   just `RangeXY`. `RangeXY` is the one that self-sustains a loop because it fires once on mount (with the
   default range, before any user action) in addition to on every zoom/pan. A subscriber that writes a
   never-repeating value from that task (a counter is the common case) keeps re-invalidating the output forever;
   I re-verified this myself post-investigation (432 `RuntimeError: BokehModel was closed` tracebacks from one
   page load with a counter-based subscriber). **Fix, also re-verified myself:** store the stream's actual value
   (`range_val.set((x_range, y_range))`) instead of a counter -- `reactive.Value.set()` already skips
   invalidation when the new value equals the old one, so the loop can't sustain itself once the range stops
   changing. 0 tracebacks across a full session with this pattern, including a real box-zoom gesture that
   correctly updated a "points visible" summary from 244/244 to 9/244. This is now
   `examples/10_zoom_range_summary.py` in the guide. Repro (broken counter version) still at
   `docs/widget-guides/holoviews/repros/rangexy_render_loop_repro.py`.
3. **[docs/up, LOW-MEDIUM] hvPlot silently drops `active_tools=` passed as a plotting kwarg.** Passing
   `active_tools=["box_select"]` directly to `df.hvplot.scatter(...)` adds nothing observable -- pan stays the
   default drag tool. The working form is `tools=["box_select"]` as the hvPlot kwarg (adds the tool) plus
   `.opts(active_tools=["box_select"])` chained afterwards (makes it default-active). Verified by toggling each
   piece independently and checking the resulting toolbar/selection behavior. This is also the mechanism behind
   why a `link_selections`-wrapped composite `Layout` needs `active_tools=["box_select"]` on each element -- see
   the guide's current Gotchas list (and `../investigations/narrow-canvas-and-subclass/INVESTIGATION.md`) for the
   retraction of an earlier, incorrect "narrow panel width" framing of the same underlying fix.
4. **[sw/bokeh boundary, LOW, cosmetic] A successful box-select on a `link_selections`-wrapped multi-panel layout
   logs a harmless exception.** After the drag (selection and every downstream output are correct), the server
   log shows 2-5 `bokeh.core.serialization.UnknownReferenceError: can't resolve reference 'pXXXX'` tracebacks from
   `BokehModel._sync_model`. Reproduces consistently on `examples/03_link_selections.py`,
   `examples/09_link_selections_dashboard.py`, and `gallery/template_crossfilter.py` -- i.e., it looks like a
   property of `link_selections` + a multi-panel `GridPlot`, not any one example's code. Never observed to affect
   the final correctness of the selection in any of my tests, so I call it out as a "don't worry about it" item
   in the guide rather than a real limitation, but it would be worth a shinywidgets or jupyter_bokeh issue since
   it's pure log noise a user would reasonably worry about.
5. **Not reproduced / already fixed, re-verified from the old report:**
   - The old report's "explicit height + no `fillable=True` collapses to a sliver" bug does **not** reproduce.
     Tested `@render_holoviews(height="250px")` with and without `fillable=True`: both give a correctly-sized
     240px-tall canvas. Matches the CHANGELOG entry for the 0.8.x sizing fixes.
   - The old report's jupyter_bokeh-CDN-fallback-when-offline issue doesn't apply: the `holoviews` extra now pins
     `jupyter_bokeh>=4.1`, which serves its JS locally.
   - I did **not** re-verify the old report's "dark theme half-applied" finding (time budget) -- dropped from this
     guide rather than carried forward unverified. If it still reproduces, it belongs in a future pass.
   - I did **not** re-verify the old report's shiny-&lt;1.9 flush-ordering workaround. The current `shiny>=1.9.0`
     floor in `pyproject.toml` and the design-candidates doc both say this class of bug depends on "shiny >= 1.9's
     self-requesting flush," and every stream/`link_selections` example in this guide works correctly with no
     flush workaround on shiny 1.9.0 -- so I'm confident it's resolved, but I didn't specifically re-test against
     an older shiny to confirm the regression would still appear there.

## Judgment calls for the maintainer to revisit

- **Restored the richer showcase design** (sidebar day filter + a second, separate click-for-detail
  `@render_holoviews` output alongside the crossfilter) once the sidebar and second-output findings were
  retracted. The crossfilter card keeps the full row width as a layout preference (not a bug workaround -- see the
  retraction above); the detail plot and table sit in a row below instead of a column beside it. Verified end to
  end: sidebar filter, 3-panel crossfilter (244/244 -> 195/244), tap-for-detail, and the table all work together in
  one app.
- **Did not attempt to root-cause the log-noise exception (#4).** I confirmed it doesn't affect correctness but
  did not read HoloViews/Panel/bokeh `GridPlot` source to explain the mechanism. Would benefit from a maintainer
  with more HoloViz-internals context; did not open an upstream issue.
- **The "exception log noise" item (#4)** I chose to present as a non-blocking cosmetic issue rather than a
  gotcha a user must work around, since I never saw it affect correctness. A maintainer more worried about
  support-ticket noise from users seeing Python tracebacks might want it elevated.
- **Trust but verify, applied to myself this round:** two of my own original four findings (sidebar, second
  output) turned out to be test-harness false positives, caught by a follow-up investigation re-running my exact
  repro files with a corrected drag region. I re-verified the retraction myself (not just trusted the
  investigation's report) before updating the guide, and I'd recommend the same discipline for any "doesn't
  fire"-shaped finding in this guide or others: confirm with a drag/gesture that visibly and substantially
  changes the plotted data, not just "did the count change," since a large but non-exclusionary selection box on
  a skewed dataset can look identical to a broken callback.

## Editor's notes for the website

- Strongest sections: "Crossfilter with zero callbacks" (quick start variant) and "Pattern 3: crossfilter
  dashboard" are the best screenshots and the most HoloViz-distinctive content -- lead with these if trimming.
  The gapminder before/after pair (04) is probably the most immediately legible screenshot in the whole guide
  (classic, recognizable chart, obvious before/after).
- The "Updating the widget from Python" in-place-vs-rerender example (07) is conceptually important but the
  screenshot pair needs the reader to notice an axis range difference, which is less visually obvious than the
  crossfilter dimming screenshots. Consider a tighter crop or an annotation if this goes on the website as-is.
- Candidate for trimming on a shorter page: the "Datashader and GeoViews" paragraph under "What you can build" is
  pure pointer text with no snippet of its own; could move to a single sentence in the intro instead.
- The Gotchas section has 8 items; I kept all of them because the first few are freshly-verified, high-impact
  findings specific to this integration (not generic Bokeh/HoloViz trivia), and the brief says to report bugs
  found, not just the happy path. If the website wants a shorter gotchas list, I'd keep the first 3 (the
  `link_selections`/`active_tools` default, Tap+link_selections, RangeXY) and fold the rest into a single
  compressed paragraph.
- Possible shinywidgets feature idea (not acted on, out of scope for a guide): a small helper like
  `stream_value(stream, "event_name")` that does the "subscribe, set a reactive.Value, reset on re-render" dance
  for the user, matching the reset-on-re-render behavior that accessors get for free elsewhere. Would directly
  address the "no accessors" gap for this renderer family (holoviews, and by extension panel) without the design
  doc's full `reactive_depend`-for-`param.Parameterized` scope. Flagging for the coordinator/maintainer, not
  implementing.

## Update 2026-11-11 (main @ 32ca7035)

- shinywidgets commit: `main` @ `32ca7035` (worktree `main-wt`). Same library versions as the prior pass (shiny
  1.9.0, holoviews 1.23.2, hvplot 0.12.2, panel 1.10.0, bokeh 3.10.1, jupyter_bokeh 4.1.0), Python 3.13.17.
- **Re-verified the #411 coercion-isolation fix directly on this commit** (it was already reflected in this
  guide's text from the original authoring pass, but the update brief asked every guide to re-confirm it): ran
  `repros/rangexy_render_loop_repro.py` (a `RangeXY` subscriber doing `range_count.set(range_count.get() + 1)` --
  the exact read+write counter shape that looped before the fix) fresh against this commit. Result: `range_count=1`
  after page load, **zero** `RuntimeError: BokehModel was closed` lines in the server log (previously 432+ from
  one page load). Confirms the fix holds on current main, not just at the commit it originally landed on.
- **No narrative simplification needed beyond what the original pass already did**: this guide's "Continuous
  streams: RangeXY needs an idempotent subscriber" section and Gotchas entry already correctly frame the
  idempotent-range pattern as good practice (avoids wasted invalidation) rather than a correctness requirement
  (avoids a crash) -- that correction happened during original authoring, before this update brief's window. I
  did not find simpler code to teach here: storing the range tuple instead of a counter is the natural way to
  read "current zoom range" regardless of the fix, so there's nothing to delete.
- **Confirmed `param(name)` does not reach `render_holoviews`** (the update brief asked every guide to verify
  this, not assume it): `render_holoviews` in `shinywidgets/_render_widget.py` has no `param()` method and does
  not override `_dynamic_accessor_spec()` (the hook that makes `param(name)` exist, declared only on
  `render_panel`). HoloViews objects render *through* Panel internally, but that's an implementation detail --
  `render_holoviews` itself never exposes the accessor. No mention of `param(name)` was in this guide and none
  was added (the stream-subscriber recipe remains the only interaction mechanism).
- Updated the "Beyond streams: `reactive_read`" paragraph to also name `.read("trait")` (the new `#437` generic
  accessor-or-trait reader every renderer gets) alongside `reactive_read(x.widget, "trait")`, and to say plainly
  why neither is useful here: `render_holoviews` has no accessors for `.read()` to prefer, and a `BokehModel`'s
  own traits (`combine_events`, `comm`, `keys`, `layout`, `log`, `render_bundle`, `tabbable`, `tooltip`) don't
  reflect anything HoloViews-specific.
- Deleted the stale "that's different from the other renderers' accessors, which reset to `None` on every
  re-render automatically" line in the stream-subscriber recipe section (`#437` retired the reset-to-`None`
  behavior everywhere else months ago; this guide's own framing hadn't been updated to match). Replaced with an
  accurate comparison: the manual `reactive.Value` here behaves like the "kept across re-render until the user
  interacts with the new widget" category accessors use elsewhere, just managed by hand since streams have no
  accessor machinery.
- No other PRs in 00f90249..32ca7035 (panel `param()`, ECharts, the renames, new plotly/cytoscape/plotnine
  accessors, debounce changes) touch anything this guide documents; `render_holoviews` itself is otherwise
  unchanged. Re-read the class in `shinywidgets/_render_widget.py` to confirm.
- Did not re-run every example file in the browser this pass (none of their *code* changed, only two prose
  passages in `guide.md`); re-ran only the one repro needed to verify the #411 re-check and confirmed via source
  reading that no accessor-related code applies to this renderer. Per the brief, text-only `guide.md` edits don't
  require a fresh run unless they add a new behavior claim, which the two edits above do, and both are backed by
  the repro run and the source read documented above.

### Bugs found (2026-11-11)

None newly found. All "Bugs found" items from the previous pass stand as previously classified (Tap+link_selections
unconfirmed; RangeXY loop fixed -- re-confirmed above; hvPlot `active_tools=` kwarg still silently dropped;
`UnknownReferenceError` log noise still cosmetic). No PR in this update window (00f90249..32ca7035) touches any
of them.

## What I dropped from the old report and why

- "HIGH: stream and selection updates are invisible until the next client message on shiny <= 1.8" -- the floor
  is now `shiny>=1.9.0`; not reproducible, not applicable to current main.
- "HIGH (fixed upstream): offline rendering blank with jupyter_bokeh 4.0.5" -- extra now pins `jupyter_bokeh>=4.1`;
  not reproducible.
- "MEDIUM: default plots don't fill and get clipped" -- kept as a plain capability note ("pass `responsive=True`"),
  not a bug; it's documented, intentional default behavior, not a limitation worth a gotcha entry.
- "MEDIUM: responsive Bokeh content collapses inside `output_widget(height=...)`" -- not reproduced; see Bugs #6.
- "MEDIUM: a module-level link_selections leaks across sessions" -- kept, but reframed as expected Shiny Core
  behavior (any shared top-level mutable object has this problem) rather than a holoviews-specific bug; stated
  once in the recipe section rather than as its own gotcha.
- "LOW-MEDIUM: dark themes are half-applied" -- dropped, not reverified (time budget); see Bugs #6.
- "LOW: `.opts()` raises without `hv.extension('bokeh')`" -- kept, reverified, now in Installation + Gotchas.
- "Behavior to document: `render_bokeh(hv.render(x))` is static" -- dropped; this is just restating what
  `render_bokeh`'s own guide already documents about plain bokeh figures having no Python callbacks, not something
  specific enough to this guide to repeat.


## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example -- cites this guide's own existing "Datashader and GeoViews" subsection and links out to the datashader guide's new Large data section for the measured numbers, since rasterize() is datashader's API, not a separate holoviews-specific one.
