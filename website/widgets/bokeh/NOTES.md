# NOTES: bokeh guide

## Versions

- bokeh 3.9.2, jupyter_bokeh 4.1.0, shiny 1.9.0, ipywidgets 8.1.9, bokeh_sampledata (latest, pulled via `uv run
  --with bokeh_sampledata` for the real-data examples; not part of the `shinywidgets[bokeh]` extra).
- shinywidgets commit: `main` as of 2026-10-30, including #388 ("don't drop comm messages that arrive before the
  model registers") merged shortly before this pass started.
- Date: 2026-10-30.

## Verification log

Every file below ran in headless Chromium (`--use-angle=swiftshader --enable-unsafe-swiftshader
--ignore-gpu-blocklist`, 1280x800, `device_scale_factor=2`) via `shiny.run.run_shiny_app` + Playwright, screenshotted,
and the screenshot was read with the Read tool before being referenced in `guide.md`.

| File | Ran | Screenshot | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes | n/a | n/a |
| examples/02_layouts.py | yes | yes | n/a | n/a |
| examples/03_bokeh_widgets.py | yes | yes (before/after) | `Select` change | n/a (raw `on_change`) |
| examples/04_draw_tool.py | yes | yes (before/after) | click to add a point (`PointDrawTool`) | n/a (raw `on_change`) |
| examples/05_theme.py | yes | yes | n/a | n/a |
| examples/06_js_link.py | yes | yes (before/after) | drag slider | n/a (client-only) |
| examples/07_selected.py | yes | yes (before/after) | box-select | `selected()` -> `[1, 2, 3]` |
| examples/08_selected_rows.py | yes | yes (before/after) | box-select | `selected_rows()` -> rows b/c/d |
| examples/09_tapped.py | yes | yes (before/after) | click | `tapped()` -> `(5.00, 5.00)` |
| examples/10_zoomed.py | yes | yes (before/after) | wheel zoom | `zoomed()` -> new x/y ranges |
| examples/11_multiple_sources.py | yes | yes (before/after) | box-select on "west" only | raw `source.selected.on_change` -> `('west', [0, 1])`; "east" untouched |
| examples/12_rate_limiting.py | yes | yes (5 shots: before, default/instant x immediate+settled) | identical box-select on two outputs | `rate_delay=0` reports immediately; default plot still `None` at the same instant, settles to the same value ~250ms later |
| examples/13_update_in_place.py | yes | yes (before/after) | pan + slider drag | n/a (in-place update); pan survived the data change |
| examples/14_linked_brushing.py | yes | yes (before/after) | box-select | `selected_rows()` -> live count/mean; cross-plot highlight confirmed visually |
| examples/15_lasso_to_histogram.py | yes | yes (before/after) | box-select | `selected()` feeds a separate `render_matplotlib` output (cross-widget) |
| examples/16_tap_to_detail.py | yes | yes (before/after) | click on a real data point | `tapped()` -> nearest-station lookup matched the clicked point exactly |
| gallery/template_linked_scatter.py | yes | yes (before/after) | box-select | `selected_rows()` -> table of selected iris rows |
| gallery/showcase_periodic_table.py | yes | yes (before/after) | box-select (data-coordinate driven, not fractional) | `selected_rows()` -> 12 alkali/alkaline-earth elements, cross-plot highlight confirmed |

Accessor coverage: **all 4 accessors verified with a real Playwright-driven gesture** (`selected`, `selected_rows`,
`tapped`, `zoomed`). No accessor needed a fallback verification method (all gestures are ordinary mouse
click/drag/wheel, nothing WebGPU/canvas-picking that Playwright can't hit).

## Bugs found

**shinywidgets (main), none found** that affect the documented behavior. Everything in the `render_bokeh`
docstring checked out against actual browser behavior:
- Accessor reset-on-render, single-source `TypeError`, debounce default and `rate_delay=0` override, `RuntimeError`
  when reading an accessor inside its own render function -- all verified directly (not just by reading the
  source).
- The old report (`docs/widget-reports/bokeh/report.md`, 2026-10-22) flagged `as_widget_bokeh` forcing
  `sizing_mode="stretch_both"` regardless of user sizing, and explicit-height outputs collapsing to ~47px. **Both
  are fixed on current `main`** (`bokeh_layout_defaults()` in `_render_widget_base.py` now checks the figure's
  actual `sizing_mode`, and `BOKEH_SIZING_PROPS` in `_as_widget.py` only stretches a `figure` that has none of
  `width`/`height`/`sizing_mode`/`aspect_ratio` set) -- confirmed by building `examples/02_layouts.py`'s 2x2
  `gridplot` and `examples/11_multiple_sources.py`'s two explicitly-ranged, `stretch_both` figures, both of which
  size correctly.

**Upstream (jupyter_bokeh), still present on 4.1.0, verified fresh (not inherited from the old report):**
1. **Raw `on_change`/`on_event` callbacks fire twice per browser-driven change.** Built a minimal repro
   (`scratchpad/.../double_fire_app.py`, not kept in the guide dir) with a hand-written
   `source.selected.on_change("indices", ...)` counter next to `plot.selected()`. One box-select gesture: the
   accessor correctly showed `[1, 2, 3]` once; the raw counter read 2. This is a genuine, currently-present
   upstream quirk (the accessors' internal "input priority" already absorbs it), documented in Gotchas since any
   user writing their own raw callback (as in the Bokeh-widgets, draw-tool, and multiple-sources examples) needs
   to know their callback isn't idempotent by default.
2. **Re-rendering leaks BokehJS view objects.** Reused `tests/playwright/bokeh_accessors/app.py`'s `#rerender`
   button and polled `Object.keys(window.Bokeh.index).length` across 6 re-renders: `[2, 4, 6, 8, 10, 12]` --
   grows by exactly 2 every time, never shrinks. Matches the old report's finding; still true on current
   `jupyter_bokeh` 4.1.0. Documented as a gotcha (avoid high-frequency re-renders; prefer in-place updates).

Both upstream items are long-standing `jupyter_bokeh` limitations, not shinywidgets regressions, and not
something this pass should fix (per the brief). Worth a short upstream issue each, but that's outside this task.

## Judgment calls

- **Box-select over lasso-select for every automated gesture.** Lasso needs a closed polygon path; Playwright can
  draw one, but a simple two-point drag (easiest to script and to explain in a screenshot) only works for
  box-select. Every example that needs a reliable, scriptable drag sets `active_drag="box_select"` even when
  `lasso_select` is also offered in the toolbar. A human user gets both tools either way.
- **Auto-ranged figures need deliberately-chosen gesture coordinates, or explicit ranges.** Early iterations of
  `examples/07_selected.py` picked box corners *exactly at* the data's max/min (e.g., `y=5.5` when the highest
  point was `y=5`), relying on Bokeh's default `DataRange1d` padding to contain it. The padding was too thin: the
  corner mapped to a pixel just *above* the canvas (overlapping the page title), so the mousedown never reached
  the plot and the gesture silently did nothing. Fixed by giving the figure an explicit `x_range`/`y_range` that
  comfortably contains the gesture. Pattern worth remembering for any future bokeh Playwright work in this repo.
- **Periodic-table showcase drops noble gases and lanthanides/actinides.** `bokeh_sampledata`'s `periodic_table`
  has no recorded electronegativity for the 7 noble gases and no single periodic-table `group` for the
  lanthanides/actinides (`group == "-"`). Dropped both (64 of 118 elements remain) for a clean, fully-populated
  grid rather than handling the ragged edge cases in a gallery demo.
- **Showcase gallery app pivoted from synthetic star data to the real periodic table dataset** after the
  coordinator's broadcast update preferring real/recognizable data for hero/quickstart/gallery content. The
  synthetic Hertzsprung-Russell-diagram version worked and looked good, but there's no small, locally-available
  real star catalog bundled with any installed package, so I chose a different real dataset (the periodic table)
  that supports the same "two linked views + dark theme + in-place restyle" structure instead of keeping the
  astronomy theme with fake data. The old synthetic version is not kept anywhere in this directory.
- **`examples/12_rate_limiting.py` uses two independent `render_bokeh` outputs** (one default, one
  `rate_delay=0`) rather than one output with a `rate_policy=`/`rate_delay=` input control, so the before/after
  screenshots can show the *same* gesture against both policies at the *same* instant. A single reconfigurable
  output would need a re-render to change its rate policy, which would also reset the plot -- a confusing demo.

## Dropped from the old report, and why

- **"Models must be owned by only a single document" cross-session guard** (old report's #2, item 3): this
  describes a Python-level Bokeh `Document`/model ownership conflict (e.g. a module-level `figure` reused across
  Core sessions), not something shinywidgets's own `foreign_or_closed_widget` check covers (that one guards
  ipywidget ownership, which is a layer above the Bokeh document). The current `render_bokeh` docstring already
  states the right practice ("create bokeh models per session"), so this is adequately covered as a gotcha
  without re-litigating whether shinywidgets should add a second guard -- that's a feature request, not a bug,
  and it's already filed implicitly by the old report.
- **jupyter_bokeh 4.0.5's missing local JS / CDN fallback mismatch** (old report's #3.6): `pyproject.toml` now
  floors `jupyter_bokeh>=4.1` in the `bokeh` extra, so a fresh `pip install shinywidgets[bokeh]` can no longer
  resolve the broken 4.0.5 wheel. Non-issue on current `main`; dropped entirely rather than listed as a historical
  footnote.
- **Lasso drags starting outside the plot frame throw "Assertion failed"** (old report's #3.9, upstream BokehJS):
  not re-verified this pass. It's a narrow edge case (a user dragging a lasso from the axis margin), already
  attributed to upstream in the old report, and not something a guide reader is likely to hit if they drag inside
  the plot frame as the examples show. Left out per the brief's "don't list hypothetical issues" -- re-verifying
  it would cost time this pass is better spent on (this is explicitly a long-tail limitation, not a regression).
- **100k/1M-point WebGL performance numbers** (old report's #3.10): didn't re-run; a performance characterization
  is a reasonable thing for a reader to want, but re-measuring it accurately needs a controlled, idle machine,
  which this shared multi-agent box isn't. Mentioned nowhere rather than republished with stale/unreliable
  numbers.
- **Full "scorecard" and star ratings**: this guide is teaching material, not an evaluation report; dropped the
  framing entirely per the brief ("something much better aimed at teaching users what's possible").

## Pairs with

- `matplotlib` -- `examples/15_lasso_to_histogram.py` drives a `render_matplotlib` histogram from a Bokeh
  `selected()` list. Good candidate for a cross-cutting "linking different widget types" article.
- `reactable` / `itables` -- not built as a full example (kept the linked-view examples single-widget-family
  plus the one matplotlib crossover to avoid padding), but `selected_rows()` is a plain `pandas.DataFrame`, so it
  drops into `@render_reactable`/`@render_itables` exactly like the `@render.data_frame` usage in
  `examples/08_selected_rows.py` and both gallery apps. Worth a one-line callout in a cross-cutting article.
- `holoviews`, `panel` -- both render through Bokeh under the hood (same `jupyter_bokeh.BokehModel`), but get no
  accessors of their own (their streams must exist before the plot is built, per the design doc). Linked in
  "Learn more" and the intro's "choose this vs. siblings" paragraph; no shared example needed since their guides
  cover the HoloViews/Panel side of that boundary.

## Editor's notes for the website

- **Strongest material:** the accessor reference table + the four verified accessor sections; the linked-
  brushing example (`14_linked_brushing.py`, also the hero image) and the periodic-table showcase are the most
  visually compelling and the clearest demonstrations of "why Bokeh" (real two-way object model, not just
  event callbacks).
- **Cuttable for a shorter page:** "Bokeh's own widgets" and "Client-only interactivity" in "What you can build"
  are the least Shiny-specific (they're close to vanilla Bokeh demos) -- cut first if the page runs long. The
  "Several ColumnDataSources" subsection is important to keep (it's the direct answer to "what if I have more
  than one source", called out explicitly in this guide's assignment) even though it's a smaller audience than
  the main accessor sections.
- **Rate-limiting section** leans on a side-by-side comparison that's a little more setup than a typical snippet;
  if trimmed, keep at minimum the two "immediate" screenshots (`12_rate_limiting_default_immediate.webp`,
  `12_rate_limiting_instant_immediate.webp}`) and one sentence -- they tell the whole story on their own.
- Unused-but-captured screenshots (kept in `img/` as verification evidence, not referenced from `guide.md`):
  `12_rate_limiting_before.webp`, `12_rate_limiting_default_settled.webp`, `12_rate_limiting_instant_settled.webp`
  (show both plots converging to the same selection ~250ms later -- confirms the debounce actually catches up,
  not just that it's delayed), `gallery_linked_scatter_before.webp`, `gallery_periodic_table_before.webp`.

## Cross-cutting finding for the coordinator (not bokeh-specific)

Confirmed independently (coordinator later broadcast the same finding): **a bare top-level module docstring in a
Shiny Express app renders as visible page text.** Shiny Express auto-displays top-level expression statements,
and a docstring is just a string-literal expression statement. Repro kept in scratch
(`scratchpad/.../repro_docstring.py`). Every gallery file in this guide uses a `#`-comment header instead, with a
one-line note in the file explaining why (in case a future editor "cleans it up" back into a docstring).

## Update 2026-11-11 (main @ 32ca7035)

Versions: bokeh 3.10.2, jupyter_bokeh 4.1.0, shiny 1.9.0, worktree
`/private/tmp/claude-502/.../ce388f54.../scratchpad/main-wt`. Read `shinywidgets/_bokeh.py`,
`shinywidgets/_bokeh_accessors.py`, and `render_bokeh`'s docstring in `shinywidgets/_render_widget.py` directly
against current `main`; ran `gh pr view 435,437 --json body -q .body` for the two PRs that touch this guide.

What changed in the guide and why:

- **Accessor reference table reformatted** to the brief's new columns (`before any interaction` /
  `across re-render`, replacing `fires when` / `None` means`). Content is accurate: `selected()` seeds `[]`;
  `zoomed()` seeds from real default ranges or `None`; `tapped()` starts `None`. On re-render, `tapped()` is
  **kept** (last tap from the old plot, until the new plot is tapped); `selected()`/`zoomed()` **re-seed** from
  the new plot (a widget-owned selection/viewport, per #437's framing). This matches `_bokeh_accessors.py`
  exactly (`attach_selected`/`attach_zoomed` both call `emit()` once at attach with the new widget's current
  state; `event_attach("tap")` has no such seed call).
- **Fixed two stale paragraphs that contradicted the docstring and table.** The accessor-reference intro used to
  say "a re-render ... every accessor resets: event-kind values ... go back to `None`" and "Updating the widget
  from Python" said "every accessor resets too" -- both wrong under the current (`[]`/kept/re-seeded) semantics;
  rewrote both to match the table.
- **Removed the "re-rendering leaks BokehJS view objects" gotcha.** This was accurate against the pre-#435
  `main`, but #435 ("drop bokehjs root views from `Bokeh.index` when a `BokehView` is removed") fixes it.
  Verified directly: re-ran `tests/playwright/bokeh_rerender_cleanup` (passes) and polled
  `window.Bokeh.index` across 7 re-renders of `tests/playwright/bokeh_rerender_cleanup/app.py` -- stays at a
  constant 2 entries, never grows (`scratchpad/agents/plot-sel/verify_bokeh_index.py`). Per the brief, deleted
  rather than noted as "now fixed."
- **Fixed `12_rate_limiting.py`'s screenshots and prose, which showed stale `None` text.** `selected()` returns
  `[]` before the debounce settles, not `None` (the guide's own accessor reference already said this; the
  rate-limiting screenshots and caption hadn't been updated to match). Regenerated
  `12_rate_limiting_{before,default_immediate,instant_immediate,default_settled,instant_settled}.webp` and the
  caption now says "still `[]`" instead of "still `None`".
- **Converted the narrative to "attaches at render, no warm-up"** language per #437 (no prior warm-up idiom was
  present in this guide to delete -- it was already written assuming a seeded/retained model for `selected()`
  and `zoomed()`, just with inconsistent prose in the two spots fixed above).
- **No `reactive_read()` conversions needed.** `BokehModel` genuinely has no useful synced traits (verified
  against `jupyter_bokeh` 4.1.0's trait list, as the existing "Beyond the accessors" section already states), so
  there is nothing to convert to `.read()`. Bokeh's own `on_change()`/`on_event()` bridge remains the right tool
  for everything the four accessors don't cover.
- **New example: "Reading an accessor on demand"** (`examples/17_download_selection.py`), added to "Reacting to
  user interaction" after "Rate limiting". A `@render.download_button` handler reads `plot.selected_rows()`
  fresh each time it's invoked -- the headline new capability (no warm-up needed for a reader that only runs
  occasionally). Verified: box-selected 3 of 5 points, clicked download, read the downloaded CSV's bytes back in
  Playwright -- `x,y,name / 3,1,c / 4,3,d / 5,5,e`, matching the box. Screenshots
  `17_download_selection_before.webp` / `17_download_selection_after.webp`.

Verification status:

| File | Ran | Screenshot looked at | Gesture | Accessor confirmed |
|---|---|---|---|---|
| `examples/12_rate_limiting.py` (re-verified, screenshots regenerated) | yes | yes (5, replaced) | box-select on both plots | `selected()` -> `[]` immediately after a debounced plot's own gesture, `[0,1,2,3,4]` after ~250ms; `rate_delay=0` plot resolves in well under 250ms |
| `examples/17_download_selection.py` (new) | yes | yes (before/after) | box-select, then click download | `selected_rows()` read inside `@render.download_button`, content verified byte-for-byte |
| `tests/playwright/bokeh_rerender_cleanup` (existing test, re-run as evidence) | yes | n/a | button click x7 (re-render) | `window.Bokeh.index` length: `[2,2,2,2,2,2,2]` (was `[2,4,6,8,10,12]` pre-#435) |

All 4 accessors (`selected`, `selected_rows`, `tapped`, `zoomed`) remain verified with real gestures (prior pass
+ this pass's rate-limiting re-check); no regressions found in their core behavior.

Previously-filed "Bugs found" items this pass re-checked:

- **#1 (raw `on_change`/`on_event` fires twice)**: not re-verified this pass; nothing in the 33 new commits
  touches this, and it's an upstream `jupyter_bokeh` property-callback quirk, not accessor-redesign-related.
  Left in the guide's Gotchas unchanged.
- **#2 (BokehJS view leak on re-render)**: **fixed by #435**, confirmed above. Removed from Gotchas.

New, tentative finding (not added to Gotchas -- see reasoning):

- **Possible race when two separate `render_bokeh` outputs' debounced accessors fire with near-zero gap.**
  While hunting down the stale `None` screenshots, I found that dragging a box-select on one debounced
  `render_bokeh` output immediately followed (same Python call, no `time.sleep()`) by a box-select on a second
  debounced output on the same page sometimes left the *first* output's `selected()` stuck at `[]` forever
  (observed for 2+ seconds, never settling) in `examples/12_rate_limiting.py`. Adding as little as a 100ms gap
  between the two gestures made it resolve reliably every time (confirmed across several repeated runs). I did
  not chase the root cause (could be a genuine debounce-timer bug in `_accessors.py`'s `RateLimiter`/
  `loop_schedule`, or an artifact of firing two Playwright CDP mouse sequences back-to-back with literally zero
  wall-clock gap, which a human using a mouse can't produce). Not filed as a confirmed bug or added to the
  guide's Gotchas since I couldn't rule out the latter and it needs an unrealistic input pattern to trigger;
  flagging here in case another agent hits the same thing elsewhere and wants to compare notes. Scratch repro:
  `scratchpad/agents/plot-sel/drive_12h.py` and `drive_12j.py` (reproduce it); `drive_12l.py`/`drive_12m.py`
  (same scenario with a small gap, resolves correctly).

Judgment calls:

- Kept the existing `examples/01-16` files and their screenshots as-is (re-read each one's surrounding prose
  against current docstrings; found no other stale claims besides the rate-limiting screenshots above).
- Added `examples/17_download_selection.py` as example 17 (append, not renumber) per the brief's preference.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views" and a new example, `examples/18_webgl_vs_canvas.py`
(two 200,000-point scatters side by side, one with `output_backend="webgl"`, one default canvas). Smoked with
`--gpu webgl` (exit 0); screenshot looked at (`img/18_webgl_vs_canvas.webp`) -- both panels render correctly in
headless Chromium with the swiftshader flags from `BRIEF.md`.

**Measured directly** (Playwright `page.on("websocket", ...)` frame capture over the whole initial render): the
two panels' `ColumnDataSource` payloads were 4,125,276 and 4,125,240 bytes -- a 0.001% difference, i.e.
effectively identical. This confirms `output_backend="webgl"` is a rendering-only switch: it doesn't change what
crosses the websocket, only how the browser draws the already-transferred data. Render-time/frame-rate
comparison between the two backends was left as a pending timing measurement for Task 11 (an HTML comment in
the guide at the exact spot, filled in below).

No new bugs found for this example.

## Update 2026-11-11 (Task 11: timing measurements)

Filled the render-time comment left pending for this wave in `guide.md`'s "Large data" section.

### Method

The committed `examples/18_webgl_vs_canvas.py` renders both panels (webgl and canvas)
on one page at once, which doesn't isolate either panel's own render time. Measured
instead from two isolated single-panel copies of the same code (same seed, same
`n = 200_000`, same `figure()`/`scatter()` calls -- byte-identical apart from which
panel is kept and the page title) in this task's scratch directory, 200,000 points
each, 3 runs apiece:

- Headless Chromium, `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist` (same flags the rest of this guide's examples use for
  WebGL).
- Elapsed time from `page.goto()` to a pixel-stable screenshot: poll `page.screenshot()`
  every 300 ms after the widget's own DOM selector
  (`.shiny-ipywidget-output .lm-Widget`) first matches, report elapsed time once two
  consecutive screenshots hash identically (SHA-1). Verified this isn't a
  false-early-stop (a risk found elsewhere this task, with renderers that have an
  async post-mount draw step -- see `articles/performance/NOTES.md`'s Task 11 update):
  a side-by-side check showed the DOM-selector match and the fully-rendered scatter
  arrive at the *same* moment for bokeh (confirmed by screenshotting right at selector
  -match time and finding the scatter already fully drawn, with zero further pixel
  changes for 30+ seconds after) -- bokeh's render is synchronous with mount, so the
  pixel-stability check here is just confirmation, not doing the real work of finding
  the completion point the way it had to for datashader/embedding-atlas.

### Raw numbers (seconds, 3 runs each)

| Backend | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| `output_backend="webgl"` | 5.121 | 5.161 | 5.088 | 5.12 (rounds to 5.1) |
| default (canvas) | 7.387 | 7.524 | 7.393 | 7.39 (rounds to 7.4) |

WebGL reached a stable, fully-drawn scatter about 30% faster than canvas at this scale,
despite shipping identical bytes (already measured, see the Task 8a update above) --
added to the guide as a second, independent benefit of `output_backend="webgl"`
alongside the already-documented pan/zoom smoothness, not a replacement for that
claim.

### Judgment calls

- **Measured from isolated single-panel copies, not the committed two-panel
  example.** Keeps each backend's own render time uncontaminated by the other panel's
  work happening on the same page/server process at the same time; the committed
  example's own job (showing the bytes are identical) doesn't need this isolation
  since bytes were already summed per-panel directly from the raw frames.
- **Did not investigate why bokeh takes several seconds at 200,000 points** (comparable
  to, e.g., plotly's multi-second times at similar scales elsewhere in the performance
  article) -- out of scope for a single comparative number; both panels build on the
  same `ColumnDataSource` construction and HTTP/websocket setup cost, which is a
  plausible shared floor neither backend can avoid.
