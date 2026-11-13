# NOTES: matplotlib guide

## Versions

- Date: 2026-10-30
- matplotlib 3.11.2, ipympl 0.10.0, ipywidgets 8.1.9, shiny 1.9.0, pandas 3.1.0, numpy 2.5.4
- shinywidgets: `main` @ `38a1796b` at the start of this session. The shared checkout's `HEAD`/branch moved
  during the session (see "Operating environment hazard" below) -- confirmed the moving parts
  (`render_quak`, `render_mols2grid` in `_render_widget.py`) never touched `render_matplotlib`/`render_plotnine`
  or `_matplotlib.py`/`_as_widget.py`'s matplotlib code, so the guide's claims are unaffected.
- Python 3.12.13, Playwright Chromium (headless; no `--use-angle` flags needed for plain 2D plots, used them
  defensively for the 3D example but it rendered fine either way).

## Operating environment hazard (not a shinywidgets bug -- flagging for the coordinator)

Partway through this session, `git branch --show-current` in the shared checkout changed twice (first to
`mols2grid-3-widget-port-clean`, later `merge-scratch`), and `shinywidgets/_render_widget.py` and
`pyproject.toml` each transiently contained literal `<<<<<<< HEAD` conflict markers, breaking
`import shinywidgets` and `uv run` for a few minutes each time. This looks like another agent running `git
merge`/rebase directly in the shared main checkout, which the brief's operating rules prohibit ("do not ... switch
branches"). I did not touch any tracked file or branch; I waited and retried (consistent with "machine is loaded,
re-run once") and confirmed via `git diff main..HEAD` that the drift (once resolved) didn't touch matplotlib-
relevant code. Worth a word to whichever agent is working on mols2grid/quak.

## Verification table

All ran via `uv run --no-sync shiny run <file> --port <9280-9298>` and were driven with real Playwright
gestures (headless Chromium, no `--force`/synthetic event dispatch except standard `page.mouse` calls).
Screenshots were all read back with the Read tool before being referenced in `guide.md`.

| File | Ran | Screenshot | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes (before/after zoom) | toolbar zoom-to-rectangle drag | n/a (no accessor) |
| `examples/02_pandas_plot.py` | yes | yes | n/a (static feature) | n/a |
| `examples/03_rotate_3d.py` | yes | yes (before/after) | 3D drag-rotate | n/a |
| `examples/04_rectangle_selector.py` | yes | yes (before/after) | `RectangleSelector` drag | n/a (raw mpl callback) |
| `examples/05_dark_mode.py` | yes | yes (light/dark) | click on `bslib-input-dark-mode`'s inner `<button>` (see Bugs found: docs) | n/a |
| `examples/06_accessor_clicked.py` | yes | yes (before/after) | click | **`clicked()` yes** |
| `examples/07_accessor_picked.py` | yes | yes (before/after) | click on a `picker=5` point | **`picked()` yes** |
| `examples/08_accessor_limits.py` | yes | yes (before/after) | toolbar zoom-to-rectangle drag | **`limits()` yes** |
| `examples/09_beyond_accessors_hover.py` | yes | yes | mouse move over canvas | n/a (raw `motion_notify_event`) |
| `examples/10_rate_limiting.py` | yes | yes | toolbar pan drag on two linked canvases | **`limits()` rate policy yes** (2 vs 11 recomputes) |
| `examples/11_inplace_vs_rerender.py` | yes | yes (zoomed, after slider) | toolbar zoom + slider drag | n/a (`.widget` pattern) |
| `examples/12_coordinate_zoom_summary.py` | yes | yes (before/after) | toolbar zoom-to-rectangle drag | **`limits()` yes** |
| `examples/13_coordinate_click_detail.py` | yes | yes (before/after) | click | **`clicked()` yes** |
| `examples/14_coordinate_select_table.py` | yes | yes (before/after) | `RectangleSelector` drag | n/a (raw mpl callback) |
| `examples/15_layout_sizing.py` | yes | yes | n/a (static) | n/a |
| `gallery/template_zoom_and_click.py` | yes | yes (before/after) | toolbar zoom + click | **`limits()`, `clicked()` yes** |
| `gallery/showcase_grid_demand_explorer.py` | yes | yes (initial/zoomed/smoothed) | toolbar zoom + click + slider | **`limits()`, `clicked()` yes** |

**Accessor coverage, all three on `render_matplotlib`:**
- `clicked()` -- verified with a real click gesture (06, 13, template, showcase).
- `picked()` -- verified with a real click on a `picker=5` artist (07).
- `limits(ax=0)` -- verified with a real toolbar zoom/pan drag, including the rate-limiting contrast (08, 10, 12,
  template, showcase).

`render_plotnine`'s `clicked()` shares the exact same `AccessorSpec` object as `render_matplotlib`'s (confirmed by
reading `_matplotlib.py`/`_render_widget.py`, not independently re-verified in a plotnine app -- that's the
plotnine guide's job).

## Bugs found

**shinywidgets: none found.** All three blockers in the old report (`docs/widget-reports/matplotlib/report.md`,
2026-10-22) are fixed on current `main`:
- B1 (pyplot figures leak across sessions): fixed by `leave_pyplot()` in `_as_widget.py` (`as_widget_mpl` calls it
  before attaching the ipympl canvas). Verified indirectly by reading the existing
  `tests/playwright/render_matplotlib_sessions` test (not independently re-run with a fresh two-session gesture,
  since the code path and the shipped test both clearly cover it and nothing in this session's diff touched it).
- B2 (per-render memory leak): fixed by the `w_ref = ref(w)` weakref in `_shinywidgets.py`'s `_open_shiny_comm`,
  exactly the fix the old report proposed.
- B3 (draw-time error crashes the session): fixed by `draw_initial_image()` in `_as_widget.py`, which draws inside
  the render rather than the deferred comm-open effect. Verified via the existing
  `tests/playwright/render_matplotlib_draw_error` test.
- S1-S3 (explicit height clips, `fill=False` still resizes, footer appears late and overflows): fixed and covered
  by `tests/playwright/render_matplotlib_fill`. Re-verified by my own `examples/15_layout_sizing.py` screenshot:
  the fixed-height panel fits cleanly with no clipping.

**Docs (shinywidgets docstring/behavior gaps worth flagging, not bugs per se):**
- `render_matplotlib`'s docstring doesn't mention that `header_visible` defaults to `True` (shows "Figure N"),
  unlike `render_plotnine`'s coercion, which explicitly sets `header_visible = False` / `footer_visible = False`.
  Confirmed by screenshot (every quickstart/feature-tour screenshot in this guide shows the literal text
  "Figure <large int>" unless I hid it myself in `15_layout_sizing.py`). Minor, but worth a one-line docstring
  addition pointing at `as_widget(fig).header_visible = False`.
- Not a shinywidgets issue, but worth noting for whoever reviews the screenshots: Shiny's own
  `bslib-input-dark-mode` custom element only wires its click handler to the inner shadow-DOM `<button>`, not the
  host element. `page.locator("bslib-input-dark-mode").click()` silently does nothing in Playwright (no error,
  theme just doesn't change); `page.locator("bslib-input-dark-mode button").click()` works. This cost real time
  during verification and will bite any future agent writing dark-mode screenshots for other guides.

**Upstream: none found** beyond what's already in the old report (ipympl's lazy DeprecationWarning on `Toolbar`
init, already a long-standing cosmetic warning, unrelated to this guide's claims).

## Judgment calls

- **Swapped synthetic data for matplotlib's own bundled sample datasets** in the quickstart, the pandas-`.plot()`
  highlight, the 3D-rotate highlight, and the click-to-pin-a-reading pattern (`matplotlib.cbook.get_sample_data`:
  `goog.npz` -- Google's 2004 IPO through the 2008 crash -- `Stocks.csv`, and `jacksboro_fault_dem.npz`, a real
  elevation survey). These ship with matplotlib itself, need no network access or extra installs, and are
  recognizable/real per the coordinator's note. Left the rate-limiting, hover, in-place-update, and
  rectangle-selector examples on small synthetic signals/toy "cars" data, since those sections are about
  demonstrating a mechanism (debounce timing, a callback pattern, a slider-driven update) rather than a dataset,
  and a named dataset would add import/cleaning complexity without making the teaching point any clearer. Also
  left the gallery template's signal synthetic on purpose -- its own header says "swap in your own data," so
  generic placeholder data is the right choice there. The showcase's grid-demand data is a plausible synthetic
  scenario (seasonal cycle, daily double-peak, heat waves); a genuinely real public grid-demand dataset would need
  a download and much more cleaning for a gallery demo, which felt like disproportionate complexity for the value
  gained.
- **Module header style:** discovered independently (before the coordinator's note on this arrived) that a bare
  top-level triple-quoted docstring renders as visible page text in Shiny Express (it replaces `sys.displayhook`
  and auto-displays top-level expression results, same as a REPL). Both gallery files use a `#`-comment header
  instead, with a one-line comment explaining why, in case a future editor wonders why this file doesn't use a
  normal docstring.
- **"Beyond the accessors" section:** ipympl's `Canvas` genuinely has nothing worth `reactive_read()`-ing (I
  enumerated every trait on a real `Canvas` instance), so that subsection leads with "there's nothing here" and
  redirects to raw `mpl_connect`/`ax.callbacks`, per the brief's fallback instruction.
- **Coordinate-view pairings:** the box-select-to-table pattern (`14_coordinate_select_table.py`) cross-links to
  the itables/reactable guides as richer alternatives to the plain `@render.data_frame` table. I didn't build a
  second version using those widgets, to keep the example dependency-free and short; flagging in case the
  coordinator wants an actual itables/reactable pairing example for a cross-cutting article.
  - **Pairs with:** itables, reactable (table side of the box-select pattern, mentioned but not built).
- **Streaming/animation claim:** I verified (not in the guide's formal examples, see
  `/private/tmp/.../scratchpad/agents/matplotlib/probe_streaming.py`) that a `reactive.invalidate_later()`-driven
  effect delivers in-place `draw_idle()` updates to the browser with zero client interaction on shiny 1.9 (4 ticks
  over 2.4s, counted via a `render.code` output, no clicks). The old report's F8 ("draws outside a flush stall")
  no longer reproduces. I only wrote this up as a sentence in "Updating the widget from Python" rather than a
  full example+screenshot, given time constraints -- a short looping example could be added later if the
  maintainer wants a dedicated animation subsection.

## What I dropped from the old report

- B1/B2/B3 and S1-S3 (the blockers and most "should-fix" items): all fixed on `main`; nothing to carry forward
  except as the above "none found" note.
- The "cross-session data leak" and "10 MB per re-render" evidence screenshots: obsolete now that the underlying
  bugs are fixed.
- The old report's scorecard/star-rating section: doesn't fit this guide's teaching-focused format.
- mplfinance-specific guidance (global rcParams mutation) and the sklearn-Display coercion gap: both true but
  narrow enough (and library-specific enough) that they didn't earn a line in Gotchas; `pandas.DataFrame.plot()`
  and `ax=`-based seaborn/statsmodels calls cover the "comes along for free" claim without needing to document
  every library's quirks.
- Performance notes on 1e5-1e6 point plots: didn't re-verify (would need a dedicated large-data example out of
  scope for this pass); dropped rather than repeat unverified numbers.

## Editor's notes for the website

- **Strongest material:** the in-place-vs-re-render pair (`inplace_vs_rerender_zoomed.webp` /
  `inplace_vs_rerender_after_slider.webp`) is the single most convincing screenshot pair in this guide -- it's an
  unambiguous side-by-side of the headline feature. If the web page needs to cut to a shorter length, keep this
  one above all others.
- The showcase gallery screenshots (`gallery_showcase_grid_demand_explorer*.webp`) are the best "hero" candidates;
  I used the plain initial-state one as the page hero since it reads cleanly at a glance, but the zoomed+pinned
  one tells a better story if the page supports a hero GIF/pair later.
- The rate-limiting section is useful but the most skippable if the page needs to shrink -- it's a secondary,
  somewhat advanced topic compared to the three accessor sections.
- "What you can build" could be trimmed to 3 items (drop dark mode) without losing much, if length is tight;
  pandas/3D/RectangleSelector together already make the "it's just matplotlib" case.

## Update 2026-11-11 (main @ 32ca7035)

Versions: matplotlib 3.11.2, ipympl 0.10.0, shiny 1.9.0, pandas 3.1.1, numpy 2.5.4, shinywidgets `main` @
`32ca7035`. Worktree venv, Python 3.13.

### What changed in the guide and why

- **#397 (header hidden by default):** rewrote the "Figure N title is shown by default" gotcha -- it's no
  longer true. `as_widget_mpl()` now sets `header_visible=False` on a coerced canvas; `render_plotnine` already
  did this. Moved the opt-back-in (`header_visible=True`) into "Layout and sizing" as a one-liner instead of a
  gotcha, since it's no longer surprising behavior. Simplified `examples/15_layout_sizing.py`'s `fixed_height`
  card and `gallery/showcase_grid_demand_explorer.py`'s chrome-hiding effect (renamed `_hide_chrome` ->
  `_hide_footer`) to drop the now-redundant `canvas.header_visible = False` line.
- **#437 (accessor semantics):** rewrote the accessor reference table to the new
  `returns | before any interaction | across re-render | rate policy` shape, and verified with a dedicated probe
  app (click + pick + zoom, then a re-render button) that `clicked()`/`picked()` **keep** their last value across
  a re-render while `limits()` **re-seeds** from the new figure. Previous wording ("resets on re-render") was
  wrong for current `main` and is removed. Added this contrast explicitly in prose under the accessor table and
  in each of the three per-accessor subsections.
- **New "Reading an accessor on demand" subsection** (the brief's headline new capability): a "Save current
  view" button reads `plot.limits()` in a `@reactive.event(input.save)` effect with no warm-up. Verified in a
  browser: clicking Save before any zoom records the figure's full extent (not `None`/an error), and clicking
  again after zooming appends the new window.
- **"Beyond the accessors" retitled** to `.read()` and `reactive_read()`, matching the new three-tier narrative.
  Content is unchanged (`Canvas` genuinely has nothing else worth reading) but the fallback is now framed as
  `plot.read(...)` falling through to `reactive_read()`, not `reactive_read()` directly.
- **Rate-limiting numbers updated**: re-verified the debounced-vs-`rate_delay=0` contrast with a fresh scripted
  drag; counts are now 2 vs. 16 (previously reported as 2 vs. 11 -- drag length/step count differs run to run,
  not a behavior change, so this is just a re-measurement).
- **Gotchas**: updated the plotnine cross-reference bullet -- plotnine's `limits()` now shares the same
  `AccessorSpec` as matplotlib's (per #402), not just `clicked()`; also notes plotnine has no `picked()`.
- No `reactive_read(x.widget, ...)` calls existed in this guide's examples (the Canvas has nothing worth
  reading), so there was nothing to convert to `.read()` in code; only the prose tier-framing changed.
- Didn't find a "warm-up" idiom anywhere in the previous version of this guide to delete -- matplotlib's
  accessors were already "state"-kind (attach-at-render, not lazy) before this pass, consistent with the old
  NOTES not flagging one.

### Screenshots replaced

All screenshots in `img/` were re-taken (nearly every one previously showed a literal "Figure <large int>"
title in the canvas header, which no longer appears by default): `quickstart.webp`/`quickstart_zoomed.webp`,
`pandas_plot.webp`, `rotate_3d_before/after.webp`, `rectangle_selector_before/after.webp`,
`dark_mode_light/dark.webp`, `accessor_clicked_before/after.webp`, `accessor_picked_before/after.webp`,
`accessor_limits_before/after.webp`, `beyond_accessors_hover.webp`, `rate_limiting.webp`,
`inplace_vs_rerender_zoomed.webp`/`_after_slider.webp`, `coordinate_zoom_summary_before/after.webp`,
`coordinate_click_detail_before/after.webp`, `coordinate_select_table_after.webp`, `layout_sizing.webp`,
`gallery_template_zoom_and_click.webp`/`_after.webp`, `gallery_showcase_grid_demand_explorer.webp`/`_zoomed.webp`/
`_smoothed.webp`. New: `read_on_demand_before.webp`/`_after.webp`.

### New/edited examples, verification status

| File | Ran | Screenshot looked at | Gesture | Accessor confirmed |
|---|---|---|---|---|
| `examples/16_read_on_demand.py` (new) | yes | yes | click Save button (before and after a zoom drag) | **`limits()` read-on-demand yes** -- console output showed `1. -2.5 to 52.5` then `2. 7.3 to 18.6` |
| `examples/15_layout_sizing.py` (edited: dropped redundant `header_visible = False`) | yes | yes | n/a (static) | n/a |
| `gallery/showcase_grid_demand_explorer.py` (edited: `_hide_chrome` -> `_hide_footer`, drops redundant header line) | yes | yes (initial/zoomed+pinned/smoothed) | toolbar zoom + click + slider | **`limits()`, `clicked()` yes** -- also re-verified zoom survives the smoothing-slider re-render (same window before/after) |
| all other `examples/*.py`, `gallery/template_zoom_and_click.py` (unchanged code, re-screenshotted only) | yes | yes | see original verification table above; re-ran each for the fresh screenshot | re-confirmed `clicked()` (06, 13, template, showcase), `picked()` (07), `limits()` (08, 10, 12, template, showcase) |

Dedicated semantics probe (not a guide example; `<scratchpad>/agents/mpl/probe_rerender.py`): click a point,
record `clicked()`/`picked()`, click Rerender, confirm both accessors still show the pre-rerender value while
`limits()` jumps to the new figure's own range. Output: `clicked() 0.484,0.500 -> 0.484,0.500` (unchanged),
`picked() 10 -> 10` (unchanged), `limits() 0.0000,1.0000 -> -0.0100,1.0100` (changed, re-seeded). Matches the
docstrings in `shinywidgets/_render_widget.py`'s `render_matplotlib` class exactly.

### Old "Bugs found" status

No shinywidgets bugs were open against this guide as of 2026-10-30 ("none found"); nothing to re-check.

### New bugs found (2026-11-11)

None. `_matplotlib.py`'s `attach_clicked`/`attach_picked`/`attach_limits` and the shared `Accessors` runtime in
`_accessors.py` behave exactly as documented.

### Judgment calls

- Kept the gallery's `showcase_grid_demand_explorer.py` effect name change (`_hide_chrome` -> `_hide_footer`)
  minimal and scoped to this one file; didn't audit other guides' gallery apps for the same now-redundant
  `header_visible = False` pattern (out of scope -- that's each guide's own agent's call).
- Picked a "Save current view" / bookmark-list pattern for the read-on-demand example rather than reusing
  `clicked()`, since `limits()` reading in a button handler is the more surprising capability (it requires no
  gesture-triggered output to exist on screen at all) and ties naturally into the existing zoom-centric examples
  in this guide.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data`: no new example. matplotlib/ipympl has no large-data mode of its own (no WebGL, no server-side rasterization); said so and pointed to Shiny's own `@render.plot` (already covered in this guide's introduction) and to bokeh/plotly/datashader as the scale-focused siblings. Did not resurrect the old report's dropped panning-frame-rate numbers (already flagged as stale in this guide's own NOTES).
