# NOTES: plotly guide

## Versions

- shinywidgets: `main` @ `e661cd65` (2026-10-30), working tree otherwise clean except for other agents'
  transient edits to shared files during this run (see "Operating conditions" below).
- plotly: 6.9.0 (plotly.js bundled inside the wheel)
- shiny: 1.9.0
- pandas: 3.1.0, polars: 2.0.0, narwhals: 2.27.1
- Playwright: Chromium, headless, 1280x800 (900 tall for sidebar layouts), `device_scale_factor=2`
- Date: 2026-10-30

## Operating conditions

This machine runs ~10 agents against the same checkout. Twice during this run, `shinywidgets/_render_widget.py`
or `pyproject.toml` had a live, unresolved git merge-conflict marker (`<<<<<<<`/`=======`/`>>>>>>>`) when I tried
to start a server, causing a transient `SyntaxError`/TOML parse error. Both resolved within 10-20 seconds (another
agent's rebase/merge completing). Not a shinywidgets bug; I added a retry-with-backoff to my scratch test harness
(`pw_helpers.py`) rather than treat it as one.

## Verification table

Every file was run with `uv run --no-sync shiny run <file>` and driven with Playwright Chromium; screenshots were
read back with the Read tool before being referenced in `guide.md`.

| File | Ran | Screenshot | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | `img/quickstart.webp` | n/a (static) | n/a |
| `examples/02_facets.py` | yes | `img/facets.webp` | n/a | n/a |
| `examples/03_scatter3d.py` | yes | `img/scatter3d.webp` | n/a | n/a |
| `examples/04_subplots.py` | yes | `img/subplots.webp` | n/a | n/a |
| `examples/05_large_data_config.py` | yes | `img/large_data.webp` | n/a | n/a (confirms modebar hidden) |
| `examples/06_clicked.py` | yes | before/after | click (real DOM point), double-click (2 variants) | `clicked()` yes |
| `examples/07_selected.py` | yes | mid-drag/after | box-drag | `selected()`/`selecting()` yes |
| `examples/08_brushed.py` | yes | before/after | lasso-drag, plus a separate deselect check | `brushed()`/`brushing()` yes |
| `examples/09_relayout.py` | yes | before/after | zoom-drag, double-click autorange | `relayout()` yes (both branches) |
| `examples/10_selected_rows_pandas.py` | yes | before/after | lasso-drag, deselect | `selected_rows()` (pandas) yes |
| `examples/11_selected_rows_polars.py` | yes | after | lasso-drag | `selected_rows(key=)` (polars) yes |
| `examples/12_rate_limiting.py` | yes | combined | slow multi-step drag, both panels | debounce vs. `rate_delay=0` yes (2 vs. 12 fires) |
| `examples/13_update_in_place.py` | yes | before/after | zoom-drag + slider (via jQuery ionRangeSlider API) | n/a (trait update); zoom survival confirmed numerically |
| `examples/14_lasso_to_table.py` | yes | before/after | lasso-drag | `selected_rows()` -> itables yes |
| `examples/15_linked_highlight.py` | yes | before/after | lasso-drag | `selected_rows()` -> cross-chart restyle yes |
| `examples/16_relayout_filter.py` | yes | before/after | zoom-drag | `relayout()` -> re-rendered second view yes |
| `examples/17_click_detail_card.py` | yes | before/after | click | `clicked()` yes |
| `examples/18_layout_sizing.py` | yes | combined | n/a | fill height (340px) vs. fixed height (300px, exact) confirmed numerically |
| `gallery/template_lasso_explorer.py` | yes | before/after | lasso + click | `clicked()` + `selected_rows()` yes |
| `gallery/showcase_gapminder_explorer.py` | yes | before/after/dark | slider (ionRangeSlider API), click, lasso, dark-mode click | `clicked()` + `selected()` yes; `batch_animate` and theme-margin fix confirmed numerically |

All gestures were driven as real mouse events (`page.mouse.move/down/up`, `page.mouse.click`, `page.mouse.dblclick`)
against computed data-to-pixel coordinates, except: the marker-size and year sliders, which are ion.rangeSlider
widgets with no native `<input>` interaction surface -- those were set via their own documented jQuery plugin API
(`$('#id').data('ionRangeSlider').update({from: ...})`), which is the same mechanism Shiny's own JS uses
internally to respond to a drag, not a shortcut around it.

## Accessor coverage summary

All 7 accessors on `render_plotly` (from `_render_widget.py`'s `render_plotly` class, not the stale design-doc
lists) were exercised with a real browser gesture and their Python-side value checked:

- `clicked()` -- yes (click; also probed double-click clearing in both its "lands on background" and "lands on
  a point" forms -- see Bugs found below)
- `selected()` -- yes (box-drag release)
- `selecting()` -- yes (mid-drag)
- `brushed()` -- yes (lasso-drag release; also probed a deselect)
- `brushing()` -- yes (mid-drag)
- `relayout()` -- yes (zoom-drag; also probed the double-click-autorange branch)
- `selected_rows(df, key=None)` -- yes, both the pandas (`key=None`, index-matched) and polars (`key=` column)
  contracts, each verified end-to-end from a real lasso to a rendered table.

## Bugs found

### shinywidgets / behavior-vs-docstring gaps (docs)

1. **`clicked()`'s docstring overstates double-click clearing.** The docstring says `clicked()` "Returns `None`
   until the user clicks, and again after a double-click or deselect." Verified: this is only true if the
   second click of the double-click lands on empty plot background. If it lands on a marker (the common case --
   double-clicking *the point you're looking at*), that click's own `plotly_click` fires *after* the
   `plotly_doubleclick` clear, so `clicked()` ends up showing that point again, not `None`. Repro:
   `docs/widget-guides/plotly/examples/06_clicked.py`; click a bubble, then double-click the same bubble --
   `clicked()` is unchanged, not `None`. Double-clicking a truly empty area does clear it. This is real
   plotly.js event ordering (two `plotly_click` events bracket one `plotly_doubleclick`), faithfully forwarded
   by the bridge -- it's a docs gap, not a bridge bug. I verified this independently (direct JS event listener)
   before writing it up.
2. **A plain click resets `selected()`/`brushed()` when `dragmode` is `"select"` or `"lasso"`**, with no
   docstring mention. Verified via `examples/07_selected.py`: lasso-select, then a single click (no drag)
   anywhere on the plot -- `selected()` goes to `None`. This is plotly.js reporting the click as a zero-area
   selection event (`points_of()` in `_plotly.py` receives no points, which publishes `None`, functionally
   identical to a deselect). Also not a bridge bug, but worth a docstring note since it surprised me and will
   surprise app authors who combine click-to-inspect and lasso-to-filter on one figure (I kept this combination
   in `gallery/template_lasso_explorer.py` deliberately, with an inline UI note, rather than avoid it).

### shinywidgets (confirmed still-current, from the old report)

3. **`output_widget`/`@render_plotly(height=...)` without `fillable=True` renders at plotly's default 360px**,
   not the height given. Still reproduces on current main (measured: container 300px, plot 360px, same numbers
   as the old report). Documented in the guide's Layout/Gotchas sections with the `fillable=True` fix.
4. **An in-place template swap drops the compact margins.** `fig.widget.update_layout(template=...)` (e.g. a
   dark-mode toggle) replaces `layout.template.layout.margin` wholesale, reverting `l`/`r`/`b` from 16 to
   plotly's 80 (measured exactly this on current main; `t` happens to stay 32 because of the separate `t==60`
   special-case in `_render_widget_base.py`). Still current; the gallery showcase works around it by always
   passing `margin=` again in the same `update_layout()` call.

### Judgment calls (things I did not chase further)

- I could **not** reproduce the old report's "explicit `layout.height` taller than its card gets clipped"
  finding with a quick, minimal repro (a `ui.card(height="250px")` containing a `layout.height=400` figure):
  on current main, inside a fillable page, the single card simply grew past its requested height instead of
  clipping the plot. This might be specific to a sidebar/multi-card layout the old report used, or might
  already be fixed; I didn't have a strong signal either way, so I dropped the claim rather than assert
  something I couldn't verify. Worth someone revisiting with the old report's exact layout if it matters.
- I did not re-verify the old report's ~5MB/re-render JS-bundle and WebGL-context-limit findings. They're real
  but are anywidget/shinywidgets-wide architecture questions, not plotly-specific content for this page --
  flagging for the coordinator rather than re-measuring.
- `gallery/template_lasso_explorer.py` combines `clicked()` and lasso-selection on the same figure, which (per
  bug #2 above) means clicking clears the lasso highlight. I chose to keep this combination, with a one-line
  UI note ("clicking also clears the lasso below"), because it's a realistic, common ask ("let me click AND
  lasso on the same chart") and hiding the limitation would be worse than naming it. A second opinion on
  whether the template should instead avoid the combination (e.g., put the click-detail example only in the
  main guide, not the gallery) would be welcome.
- Gallery/example file headers use a `#`-comment block, not a triple-quoted module docstring, because Shiny
  Express auto-displays a bare top-level string expression as page text -- a module docstring *is* exactly
  that, so it would render as a giant paragraph at the top of the app. (The coordinator also flagged this
  independently mid-task; I'd already made the same fix.)
- Dataset choice: `plotly.express.data.gapminder()` for nearly every accessor/interaction example (recognizable,
  ships with plotly, good size for a lasso/click demo), `tips()`/`stocks()`/`iris()` for the feature-tour
  section, and one synthetic dataset (`examples/05_large_data_config.py`, 200k Gaussian points) where the point
  is specifically to demonstrate scale, not tell a data story.

## Pairs with (for cross-cutting articles)

- **itables**: `examples/14_lasso_to_table.py` and `gallery/template_lasso_explorer.py` both feed
  `plot.selected_rows(df)` straight into a `render_itables` table.

## Editor's notes for the website

- Strongest sections: "Reacting to user interaction" (all 7 accessors, each with a real before/after) and
  "Coordinating multiple views" (4 complete patterns matching the brief's exact list: lasso->table, selection->
  second plot in place, zoom->filter second view, click->detail card). The showcase gallery app
  (`gallery_gapminder_after.webp`/`gallery_gapminder_dark.webp`) is the best single image if the website wants one
  hero beyond the chosen `hero.webp` (which is the same screenshot).
- Candidates to cut for a shorter page: the "What you can build" feature tour could drop to 3 items (facets, 3D,
  large-data+config) if space is tight -- subplots/dual-axis is the least essential since it's a generic
  graph_objects pattern, less specific to "why plotly in Shiny."
- The rate-limiting comparison (`img/rate_limiting.webp`, side-by-side 2-fires-vs-12-fires) is a good, concrete
  image if the website wants one callout image for "what does debouncing even do" across multiple guides.
- Extra verification screenshots exist in `img/` but aren't referenced from `guide.md` (kept for evidence, not
  bloat): `brushed_before.webp`, `brushing_mid.webp`, `click_detail_card_before.webp`,
  `gallery_gapminder_before.webp`, `gallery_lasso_explorer_before.webp`, `lasso_to_table_before.webp`,
  `linked_highlight_before.webp`, `relayout_before.webp`, `selected_before.webp`,
  `selected_rows_pandas_before.webp`. Safe to delete if the website build doesn't want unreferenced images in the
  guide's `img/` directory.

## What I dropped from the old report and why

- The entire "5MB plotly.js bundle per figure, re-evaluated on every render" performance investigation and its
  prototype (serving `_esm` by URL): real and significant, but an anywidget/shinywidgets-wide architecture
  question (affects every anywidget-based renderer, not plotly specifically), and well outside what a user-facing
  "how to use plotly" guide should carry. Worth its own cross-cutting article per the coordinator's remit, not
  this page.
- "Exceptions inside plotly callbacks are swallowed": this described the old `on_click`/`on_selection`
  trace-callback API, which the accessors supersede for the patterns this guide teaches (the guide doesn't
  recommend registering callbacks directly). I didn't re-verify whether the accessor bridge itself swallows
  exceptions in `payload`/shape functions -- the `_plotly.py` module comment states this is a hard constraint
  ("ipywidgets swallows exceptions raised here, so this must not raise"), which is a shinywidgets-internal
  contract rather than a user-facing gotcha, so I left it out of Gotchas.
- WebGL-context-exhaustion-under-many-scattergl-plots and large-data latency tables: real, but a large-scale/
  performance-benchmarking concern better suited to a dedicated "large data" cross-cutting article than this
  guide's "what you can build" tour, which only needs to establish that WebGL mode exists and roughly when to
  reach for it (I kept that one line).
- The old report's "non-issues" list (fixed upstream bugs, harmless console noise, test-harness notes): not
  relevant to a user-facing guide.
- The specific scorecard/star-ratings format: replaced with concrete, verified Gotchas instead of a subjective
  rating system.

## Update 2026-11-11 (main @ 32ca7035)

Versions for this pass: shinywidgets `main` @ `32ca7035`, plotly 6.9.0, shiny 1.9.0, pandas 3.1.1, polars
2.1.0, narwhals 2.28.0. Worktree:
`/private/tmp/claude-502/-Users-cpsievert-github-py-shinywidgets/ce388f54-2d12-4580-8021-8300841b1d00/scratchpad/main-wt`.
No `SMOKE-2026-11-11.md` existed yet when this pass started.

### What changed in the guide and why

- **Accessor redesign narrative (#437, #419/#412).** Rewrote the "Reacting to user interaction" intro and the
  accessor reference table to teach "accessors are inputs that remember": every accessor attaches at render
  (no lazy attach, no warm-up idiom -- there wasn't one explicitly written in the old guide, but the old table
  also didn't say anything about re-render behavior, which the brief required). The table's old
  `Fires when`/`None means` columns became `Before any interaction` / `Across a re-render`, and every accessor
  now states whether it's kept (`clicked`, `hover`, `selecting`, `brushing`, `relayout`, `double_clicked`,
  `legend_clicked`) or re-seeded (`selected`, `brushed`, `visible_traces`, `selected_rows`). Added matching
  one-line notes after the `clicked()`/`selected()`/`brushed()`/`relayout()` examples.
- **New accessors (#443): `hover()`, `double_clicked()`, `legend_clicked()`, `visible_traces()`.** Added a
  dedicated subsection and verified example for each (see below), plus rows in the accessor reference table
  and the front-matter `accessors:` list.
- **#401 (explicit heights, margin persistence): both Gotchas retired.** Removed the "`height=` alone doesn't
  give you that height" and "an in-place template swap resets your margins" Gotchas, rewrote the Layout and
  sizing section's height paragraph, rewrote `examples/18_layout_sizing.py` to drop the now-unnecessary
  `fillable=True` workaround, and fixed the stale comment in `gallery/showcase_gapminder_explorer.py`'s
  `_theme()` effect that claimed margins needed to be re-passed on every template swap.
- **#419/#437 (selected()/brushed() seeding/retention):** these were already correctly described as resetting
  on deselect in the old guide text; what was missing was the re-render behavior, now covered in the intro
  paragraph and per-accessor notes above.
- **`.read(name)` (#437).** Rewrote "Beyond the accessors: reactive_read" into "Beyond the accessors: `.read()`",
  explaining the named-accessor/`.read()`/`reactive_read()` tiers and reconfirming (unchanged conclusion) that
  no plotly widget trait is worth falling through to.
- **Rate limiting section:** added `hover()` to the list of 250ms-debounced-by-default accessors.
- **#398 (docstring corrections):** the clicked()-double-click and click-resets-selection gotchas were already
  correct in the old guide (that PR's findings came from this guide's own earlier pass); added one sentence to
  "Clearing semantics" connecting them to the new `double_clicked()` accessor.
- No `reactive_read(x.widget, ...)` calls existed in this guide to convert to `.read()`; the guide already used
  typed accessor methods throughout, and the `.read()` section explains the primitive without needing an
  example (no app in this guide has a reason to call outputs generically by name).

### New/edited examples and verification

All driven with real Playwright gestures (mouse move/click/dblclick/drag) against a `uv run --no-sync shiny
run` server in the worktree; every screenshot below was read back with the Read tool before being referenced.

| File | Change | Gesture | Accessor confirmed | Screenshot |
|---|---|---|---|---|
| `examples/18_layout_sizing.py` | Rewrote: dropped `fillable=True` from the fixed-height example | n/a | n/a -- measured `fixed` plot settles at exactly 300px height (was 360px before #401) | `img/layout_sizing.webp` (replaced) |
| `examples/19_hover_detail.py` | New | mouse move onto a bubble, then off | `hover()` yes (reports the point, then clears to `None` off it) | `img/hover_before.webp`, `img/hover_after.webp` |
| `examples/20_double_clicked_reset.py` | New | click a bubble, then double-click background | `clicked()` (highlight) + `double_clicked()` (reset) yes, verified via actual bar-chart marker colors read back from the DOM | `img/double_clicked_before.webp`, `img/double_clicked_after.webp` |
| `examples/21_legend_visible_traces.py` | New | click "Africa" in the legend | `visible_traces()` yes (table drops the Africa row); `legend_clicked()` yes (reads `"2,Africa"`) | `img/visible_traces_before.webp`, `img/visible_traces_after.webp` |
| `examples/22_read_on_demand.py` | New | lasso a cluster, wait, *then* click Export | `selected_rows()` read for the first time after the gesture, still reflects it -- yes | `img/read_on_demand_lassoed.webp`, `img/read_on_demand_exported.webp` |
| `gallery/showcase_gapminder_explorer.py` | Comment-only fix (margin claim) | smoke-booted + dark-mode toggle | margins stay `{l:16, t:32, r:16, b:16}` after the toggle without the (now-unneeded) manual re-pass reasoning in the old comment | not re-taken (no visual change) |

Accessor verification, all 10 named accessors plus `selected_rows()`:

- `clicked()`, `selected()`, `selecting()`, `brushed()`, `brushing()`, `relayout()`, `selected_rows()`: carried
  over from the 2026-10-30 pass, re-read against current docstrings and still accurate; not re-driven in the
  browser this pass (text-only / no new claims added beyond the re-render notes, which are copied from the
  verified docstring language in `shinywidgets/_render_widget.py`).
- `hover()`: new, verified (examples/19).
- `double_clicked()`: new, verified on cartesian (examples/20) plus two standalone probe pages (raw HTML served
  from the worktree's bundled `plotly.min.js`, no shinywidgets involved) confirming it also fires on
  `scattermap` (mapbox-family) and `scatterternary`, and does **not** fire on `scatter_3d` -- see Bugs found.
- `legend_clicked()`/`visible_traces()`: new, verified (examples/21) -- both accessors render to their own
  output (`legend_clicked()` to a `render.code`, `visible_traces()` driving the filtered summary table) and
  were confirmed against a real legend click: `legend_clicked()` read back `"2,Africa"`, and the table dropped
  the Africa row.

### Bugs found (2026-11-11)

**docs (docstring vs. verified behavior):**

1. **`double_clicked()`'s docstring lists 3D among the subplot types it's needed for, but it doesn't fire for
   `scatter_3d` on the plotly 6.9.0 bundled with this checkout.** Verified three ways: (a) in the actual
   shinywidgets app, double-clicking a `scatter_3d` scene's background never changes `double_clicked()`'s
   value; (b) a standalone HTML page (serving the same `plotly.min.js` directly, no shinywidgets) with a raw
   `gd.on('plotly_doubleclick', ...)` listener never fires it either, while the double-click instead produces
   two more `plotly_relayout` events (a tiny camera-orbit delta, then an empty-payload one) rather than a
   reset; (c) a raw DOM
   `dblclick` listener on the WebGL canvas *does* fire, confirming the browser-level double-click itself
   registers fine -- plotly.js's gl3d subplot just never translates it into a `plotly_doubleclick` emit.
   Confirmed `scattermap` (mapbox-family) and `scatterternary` *do* fire it as the docstring describes, so this
   looks specific to gl3d. Repro: `px.scatter_3d(...)` inside `@render_plotly`, double-click the rendered
   scene's background -- `double_clicked()` never changes. Not fixed; documented in the guide's Gotchas and in
   the `double_clicked()` subsection instead (which uses a cartesian demo rather than 3D, to avoid shipping a
   guide example that silently doesn't work). Not a shinywidgets bug -- the bridge forwards exactly what
   plotly.js emits.

**Previously open, now fixed (both from the 2026-10-30 pass's "Bugs found" list):**

2. `output_widget`/`@render_plotly(height=...)` without `fillable=True` rendering at plotly's 360px fallback:
   fixed by #401. Verified: `output_widget("fixed", height="300px", fillable=False)` now settles at exactly
   300px (measured via `_fullLayout.height` and the element's bounding rect).
3. An in-place `update_layout(template=...)` dropping the compact margins: fixed by #401. Verified: toggling
   `plot.widget.update_layout(template="plotly_dark")` twice (dark, then back to light) on a figure with the
   default compact margins keeps `{l:16, t:32, r:16, b:16}` throughout, with no `margin=` re-pass needed.

### Judgment calls

- Didn't re-drive the carried-over accessors (`clicked`, `selected`, `selecting`, `brushed`, `brushing`,
  `relayout`, `selected_rows`) in the browser this pass, since their behavior, docstrings, and example code are
  unchanged since 2026-10-30 and were already verified then; only the new re-render-behavior prose (sourced
  from the current, verified docstring in `_render_widget.py`) is new text about them.
- Chose a cartesian (not 3D/mapbox/ternary) demo for `double_clicked()` precisely because of Bugs-found #1 --
  using 3D would have shipped a guide example that silently doesn't work. The guide's prose still tells the
  reader which subplot types the accessor is meant for and flags the 3D gap.
- `examples/20_double_clicked_reset.py` reuses the gapminder scatter + top-15-population bar chart pairing
  (same shape as `examples/15_linked_highlight.py`'s cross-chart highlight) rather than inventing a new
  dataset, to keep the guide's example set cohesive.

## Update 2026-11-11 (C1 docstring fix, fix/accessor-c-fixes)

- The `double_clicked()` docstring no longer lists 3D among the subplot types the accessor covers (it now calls
  gl3d out as the exception: plotly.js never emits `plotly_doubleclick` there). Guide prose updated to match:
  the accessor subsection and the Gotchas entry now state the 3D gap as documented behavior rather than a
  docstring/behavior mismatch. No behavior changed; no examples re-run (text-only edit, examples already used a
  cartesian demo for this reason).

## Update 2026-11-11 (smoke follow-up: 21_legend_visible_traces fix)

- `examples/21_legend_visible_traces.py`: the smoke run's `AttributeError: 'NoneType' object has no attribute
  'loc'` was real. `summary()` read `plot.visible_traces()` unguarded, so its first run (before the browser
  reports the seed just after first draw) crashed; the output recovered on the seed's invalidation, but the
  server log showed the error and the table flashed an error state. Fixed with the documented guard
  (`req(vis is not None)`), matching the accessor's "returns None until seeded; check for it" contract.
  guide.md code block updated to stay byte-identical. Re-verified in Chromium: zero AttributeErrors in the
  server log, summary shows all 5 continents on load, clicking "Africa" in the legend greys it out, drops it
  from plot and table, and `legend_clicked()` reports `2,Africa` (screenshot looked at).

## Update 2026-11-11 (Task 8a: Large data section)

Added  after "Coordinating multiple views": moved the existing `go.Scattergl`/`render_mode="webgl"` paragraph and `examples/05_large_data_config.py` out of "What you can build" (no content changes, snippet still matches the file verbatim -- re-checked with `check_docs.py --snippets`). Appended a cross-link to the linked-views article's new brushing-at-scale pattern (Task 6 handoff, applied verbatim) noting that this guide's own lasso-to-table pattern (example 14) becomes an anti-pattern at millions of rows -- citing Wave 1's measured numbers (1M-row Scattergl lasso: ~9.45MB/drag; crashed at 5M under a live selecting() drag), not independently re-measured in this task.
