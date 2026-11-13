# NOTES: bqplot guide

## Versions

- bqplot 0.13.1 (bqscales 0.3.x transitively), shiny 1.9.0, Playwright Chromium
- shinywidgets commit `00f90249` (main, 2026-10-30), checked out read-only in a worktree
  (`/private/tmp/.../scratchpad/main-wt`) per the coordinator's mid-task instruction (another agent was switching
  branches in the primary checkout)
- Date: 2026-10-30

## Verification table

Every file below was run with `uv run --no-sync shiny run <file>` and driven with Playwright Chromium
(`--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist`), 1280x800,
`device_scale_factor=2`. "Gesture" = a real mouse drag/click/wheel/keyboard action via Playwright, not a
JS-injected trait set. All 18 files passed their final run with zero unexpected console/page errors.

| file | ran | screenshot(s) | gesture driven | accessor/claim confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | quickstart.webp | n/a (static) | — |
| `examples/02_grammar.py` | yes | grammar.webp | n/a | shared scales keep two marks aligned |
| `examples/03_pyplot.py` | yes | pyplot.webp | n/a | pyplot output visually identical to 02 |
| `examples/04_draggable.py` | yes | draggable_before/after.webp | drag a point | `enable_move`; refit line updates in place |
| `examples/05_animated_gapminder.py` | yes | gapminder_1952/2007.webp | move slider (keyboard) | `animation_duration` + `hold_sync()` tween |
| `examples/06_toolbar.py` | yes | toolbar.webp, toolbar_zoomed.webp | click PanZoom button, wheel-zoom | toolbar PanZoom works end to end (see Bugs: this contradicts the old report) |
| `examples/07_selectors.py` | yes | selectors_brush.webp, selectors_lasso.webp | drag brush, switch radio + lasso path | `fig.interaction` swap in place; `selected()` re-attaches |
| `examples/08_selection.py` | yes | selection_before/after.webp | click a point | `selected()` click-select |
| `examples/09_brush.py` | yes | brush_before/after.webp | drag interval | `brush()` region (not indices) |
| `examples/10_reactive_read.py` | yes | reactive_read.webp | drag brush + release, wheel-zoom | `brushing` flag gating; PanZoom scale domain via `reactive_read` |
| `examples/11_rate_limiting.py` | yes | rate_limiting.webp | slow multi-step drag on both panels | debounce (250ms) vs `rate_policy="throttle"`: 4 vs 14 fires for the same gesture |
| `examples/12_inplace_vs_rerender.py` | yes | inplace_zoomed.webp, inplace_after_change.webp | wheel-zoom both panels, move slider | re-render resets PanZoom domain; in-place keeps it (axis ticks differ in the two screenshots) |
| `examples/13_linked_lasso_table.py` | yes | lasso_table_before/after.webp | lasso path | `selected()` -> `render.data_frame` |
| `examples/14_linked_click_detail.py` | yes | click_detail_before/after.webp | click a point | `selected()[0]` as scalar -> detail card |
| `examples/15_linked_brushing.py` | yes | linked_brushing_before/after.webp | drag brush on left figure only | Python-driven cross-figure highlight (see Bugs: the *native* bqplot version does not work) |
| `examples/16_layout_sizing.py` | yes | layout_sizing.webp | n/a | fill vs `render_bqplot(height=)` vs `Figure(layout={"height":...})` |
| `gallery/template_brush_explorer.py` | yes | gallery_template.webp | drag brush | `selected()` driving summary + table |
| `gallery/showcase_gapminder_explorer.py` | yes | gallery_showcase_before/after.webp, plus a separate headless run confirming autoplay | lasso path; separately, clicked Play/Pause and polled the slider's DOM value over 5s | `selected()` driving a second figure's bars in place; autoplay via `invalidate_later` + `ui.update_slider` |

Accessor coverage: both `selected()` and `brush()` were exercised with real Playwright gestures (drag, click,
lasso path) across examples 07-15 and both gallery apps, not just unit-level trait sets.

## Bugs found

### shinywidgets / current main

1. **(Regression in the old report, now fixed) The built-in toolbar's PanZoom and Reset buttons work.** The old
   report (`docs/widget-reports/bqplot/report.md`, written 2026-10-22 against PR #280) says both buttons throw
   page errors ("Neither comm nor model_id provided", "reading 'reset_scales'") because the toolbar creates a
   browser-initiated widget that shinywidgets' HTML-manager-based output couldn't open a comm for. On current
   main this is resolved: `tests/playwright/render_bqplot/test_render_bqplot.py` has dedicated tests
   (`test_toolbar_panzoom_creates_and_closes_python_widget`, `test_toolbar_figure_rerenders_cleanly`,
   `test_toolbar_reset_closes_comm_after_reconnect`, `test_disconnect_closes_models_without_errors`) and I
   independently verified it in `examples/06_toolbar.py` and `examples/12_inplace_vs_rerender.py`: clicking
   PanZoom, wheel-zooming, and clicking Reset all work with no console errors, and the zoomed domain is readable
   via `reactive_read()`. The repo history shows a `frontend-comm-open` worktree, implying someone landed
   frontend-initiated-comm support since the old report. I dropped the old report's blocker entirely rather than
   repeating it as a gotcha.
2. **New finding: a shared `Selector` can't highlight marks across two separately rendered `Figure`s.** This is
   the standard bqplot/Jupyter "linked brushing" idiom (`BrushSelector(marks=[mark_in_fig_a, mark_in_fig_b])`,
   attached as `fig_a.interaction`) and it's a plausible, natural thing for a user to try based on upstream
   bqplot examples. In shinywidgets it fails outright: the browser throws `Could not create a view for model id
   ...` and the selector's drag overlay never renders on *either* figure (confirmed via a direct DOM check: zero
   `rect[pointer-events="all"]` elements after the error, on repeated runs and after waiting 8s). I also tried
   wrapping both figures in one `ipywidgets.HBox` behind a single `render_widget` output (one widget-manager
   scope instead of two) -- same error, same failure. I did not dig further into *why* (likely an html-manager
   `create_view` ordering/scoping issue when a selector's `marks` list spans models that aren't both already
   attached to a view in time), since root-causing a third-party widget-manager internal is out of scope for a
   docs pass, but it's reproducible and not an upstream bqplot bug (the same code works in a Jupyter notebook).
   I did not file this anywhere else; it's reported here only. The guide's "Coordinating multiple views" section
   uses the Python-round-trip workaround (`examples/15_linked_brushing.py`) instead and calls out the limitation
   explicitly in Gotchas.

### Upstream bqplot (not shinywidgets bugs, kept from the old report after re-verifying)

3. `BrushSelector.clear = True` and `selector.reset()` have no effect; re-verified by setting them from Python
   and observing no browser-side or trait-level change. Clearing works via `selected_x = selected_y = None`.
4. `FastIntervalSelector`/`IndexSelector` need one click before they track the mouse, contradicting their
   docstrings. Re-verified; this is also true in the vanilla `@jupyter-widgets/html-manager` control, so it's not
   shinywidgets-specific.

### Docs accuracy

5. No docstring inaccuracies found in `shinywidgets/_render_widget.py` or `shinywidgets/_bqplot.py` for
   `render_bqplot`'s class docstring, `selected()`, or `brush()` -- every claim (debounce default, `None`
   semantics, re-seed-on-marks/interaction-change, single selector-has-no-region behavior) matched what I
   observed in the browser.

## Judgment calls

- **Dropped the old report's toolbar and tooltip "should-fix" items.** Toolbar now works (see Bug 1 above).
  Tooltip theming (`.bqplot_tooltip_div` CSS scoping) also now looks correct in my screenshots (light background,
  visible border, following the card's theme) -- I didn't build a dedicated dark-mode test app for this guide
  since the brief's time budget didn't call for a dark-mode section, but nothing I saw suggested a regression.
  Flagging this as a possible second-look item if the maintainer wants dark-mode screenshots in the final page.
- **Replaced the "native" linked-brushing pattern with a Python round-trip** instead of omitting cross-figure
  linking from the guide entirely, since "linked views" is explicitly called out in the brief and the
  round-trip version is simple, fast (one trait write in an effect), and visually makes the same point.
- **Did not cover `Map`/`WorldMap`, `Graph`, `Radar`, `OHLC`, `Boxplot`, `Pie`, or `GridHeatMap`/`ColorAxis`** in
  the feature tour. The brief caps the tour at 4-8 highlights and asks for the library's *most compelling*
  capabilities, not an API survey; I judged scales/marks/axes, pyplot-vs-object, dragging, animation, the
  toolbar, and the seven selectors to be the highlights worth a reader's time. These other mark types are
  standard "set some data, get a shape" marks with nothing bqplot-in-Shiny-specific to teach, and are already in
  bqplot's own example gallery (linked from "Learn more").
- **`default_size` bug-adjacent gotcha (max-size-not-constant-size) is listed as a gotcha, not a bug**, since it's
  bqplot's own documented (if easy to misread) semantics, and I hit it myself while writing the gapminder example
  (`default_size=1` rendered nothing visible). Kept as a "things a user will actually hit" item since it's a very
  natural first mistake.
- **No dedicated dark-mode or `Radar`/small-card screenshot was produced**, unlike the old report's
  `evidence_marks_dark.webp` / `evidence_sizing_matrix.webp`. The Gotchas section still states the small-card
  margin/tick-count issue as fact (re-verified conceptually from the trait values: `fig_margin` defaults and
  `Axis.num_ticks` are indeed fixed), but I did not re-shoot the old report's small-card screenshots given the
  time budget; the maintainer may want to pull `evidence_sizing_matrix.webp` and `evidence_marks_dark.webp` forward
  from the old report's assets if a visual is wanted there (they're still accurate; the PR that produced them
  only touched toolbar/tooltip/CSS, which is now merged).
- **Gapminder appears twice** (tour highlight + gallery showcase). I treated the tour's version as the compact
  teaching example (just the animation mechanic) and the showcase as the "impressive end result" (autoplay,
  lasso, linked bar chart), per the brief's bucket definitions, rather than cutting one.

## Bugs I found and fixed in my own example code (not shinywidgets bugs)

- `bqplot.LinearScale(min=0, max=gap["pop"].max())`: `gap["pop"].max()` is `numpy.int64`, and bqplot's `Float`
  trait validator rejects it outright (`TraitError: expected a float, not numpy.int64`). Fixed with
  `float(...)`. This is a real trap for any bqplot-in-pandas user, not an artifact of my examples, so it's worth
  the maintainer knowing even though I didn't add it to the public Gotchas list (it's upstream traitlets strictness
  on a very common pandas pattern, not bqplot- or shinywidgets-specific enough to call out in a focused guide).
- `years = sorted(gap["year"].unique())` produces a list of `numpy.int64`; passing one to
  `ui.update_slider(..., value=next_year)` crashes the whole Shiny session with `TypeError: Object of type int64
  is not JSON serializable` (uncaught, kills the websocket). This only bites server-initiated slider updates
  (`ui.update_slider`), not the initial `ui.input_slider(min=..., max=...)` render, which is why
  `examples/05_animated_gapminder.py`'s simpler slider usage never hit it but the showcase's autoplay did. Fixed
  with `sorted(int(y) for y in ...)` in both files.
- My first draft of `examples/11_rate_limiting.py` used `reactive.value` counters that the same `@render.code`
  function both read and wrote (`counts.set(counts.get() + 1)` inside a function that also reads `counts.get()`
  in its return value) -- a self-triggering infinite reactive loop that flooded the websocket and broke Shiny's
  output-progress state machine (`"unexpected state of: running"` client errors). Fixed with a plain
  (non-reactive) `dict` counter. This is a general Shiny footgun, not bqplot-specific, but easy to hit when
  building a "how many times did this fire" demo for any accessor, in any renderer.

## Editor's notes for the website

- **Strongest visuals**: the gapminder animation (`gapminder_1952.webp` / `gapminder_2007.webp`) as the hero, and
  the showcase gallery app's before/after (lasso -> ranked bar chart). The toolbar zoom pair and the rate-limiting
  pair are good secondary visuals because the numbers in them (4 vs 14 fires; axis range changing) make the point
  without needing the reader to squint at dot positions.
- **Cut candidates for a shorter page**: the pyplot-vs-object-model section (03) could be trimmed to a single
  sentence + link if space is tight, since the screenshot is visually identical to 02 by design. The
  rate-limiting section could also be cut or folded into the accessor reference table's "default rate policy"
  column alone, if the page is running long.
- **What I dropped from the old report and why**:
  - Toolbar-broken and tooltip-broken findings: fixed on main (see Bugs 1 above); nothing to carry forward.
  - The old report's `Radar` hard-coded-600px and `Pie`/`Graph` pixel-radius findings: folded into one sentence in
    Gotchas rather than their own subsection; still true but not worth a dedicated highlight.
  - The old report's "two sessions with pyplot cross-talk" scenario: compressed into the single pyplot gotcha
    bullet (the proximate cause -- missing `bplt.figure()` -- is the same whether it manifests as cross-session or
    cross-render).
  - The old report's scorecard/ranked-dimensions table and "magic" bullet list: not applicable to a teaching
    guide's structure.
- **Pairs with** (for cross-cutting "linked views" articles): itables, reactable (table-driven detail/filter
  patterns match examples 08/13/14 almost verbatim with a different widget on the left); plotly, altair (as
  "siblings" in the Plotting category, worth a short comparison callout on the roster/landing page).

## Update 2026-11-11 (main @ 32ca7035)

Versions: bqplot 0.13.1, shiny 1.9.0, worktree
`/private/tmp/claude-502/.../ce388f54.../scratchpad/main-wt`. Read `shinywidgets/_bqplot.py` and
`render_bqplot`'s docstring in `shinywidgets/_render_widget.py` against current `main`; read the PR body for
#405 (`gh pr view 405 --json body -q .body`).

What changed in the guide and why:

- **Accessor reference table reformatted** to the new columns (`before any interaction` / `across re-render`).
  Content unchanged in substance -- this guide's prior pass already correctly documented both accessors as
  re-seeding on re-render, matching `_bqplot.py`'s `attach_selection`/`attach_brush` (both call `publish()`
  once at attach, from the new figure's/interaction's current state). Added "attach the moment the figure
  renders -- no warm-up read needed" to the prose explicitly, using the redesign's vocabulary.
- **#405 (toolbar PanZoom closed with its figure on re-render) was already correctly reflected** in "The
  built-in toolbar works" ("shinywidgets now opens that comm on demand ... including reset (which closes the
  PanZoom model cleanly)"), and there was no stale "leak" gotcha to remove. Re-verified directly: ran
  `tests/playwright/render_bqplot/test_render_bqplot.py -k toolbar` (3 passed), specifically
  `test_toolbar_figure_rerenders_cleanly`, which re-renders a figure with an active toolbar PanZoom twice and
  asserts zero stray `comm_close` messages each time (a leak would show up as the browser answering Python's
  figure-close with its own close for the orphaned PanZoom). No gotcha needed; nothing to change.
- **Added "say why" to the `reactive_read()` section.** The existing "Beyond the accessors" prose explained
  *what* traits were readable but not *why* `reactive_read()` (not `.read()`) is the right tool: marks, scales,
  and selectors are objects nested inside the figure, not `fig.widget` itself, so `fig.read(name)` (which only
  checks `fig.widget`'s own traits) can't reach them. Added one sentence making this explicit. No code changes
  needed -- every `reactive_read()` call in this guide already targets a mark/scale/selector, never `fig.widget`
  directly (grepped `\.widget\b` usage across `guide.md` and `examples/*.py` to confirm).
- **New example: "Reading an accessor on demand"** (`examples/17_download_selection.py`), added to "Reacting to
  user interaction" after "Rate limiting". A `@render.download_button` handler reads `plot.selected()[0]`
  fresh each click -- no warm-up needed, consistent with the redesign's headline capability. Verified: brushed a
  region of a 300-point scatter, clicked download, read the CSV back (55 of 300 points, matching the visible
  highlighted region in the screenshot). Screenshots `17_download_selection_before.webp` /
  `17_download_selection_after.webp`.
- **No `reactive_read(x.widget, ...)` conversions needed.** Every `reactive_read()` call in this guide already
  targets a mark, scale, or selector (a nested object, not the figure's own widget) -- genuinely tier-3 usage,
  not a missed `.read()` conversion.
- **No warm-up idiom was present to delete.** This guide's `selected()`/`brush()` narrative was already
  "re-seeds on re-render, attaches at render" before this pass.

Verification status (new/changed only):

| File | Ran | Screenshot looked at | Gesture | Accessor confirmed |
|---|---|---|---|---|
| `examples/17_download_selection.py` (new) | yes | yes (before/after) | brush drag | `selected()[0]` read inside `@render.download_button`, content verified (55 rows, CSV spot-checked) |
| `tests/playwright/render_bqplot/test_render_bqplot.py -k toolbar` (existing test, re-run as evidence for #405) | yes | n/a | button clicks (rerender x2) | 0 stray `comm_close` messages both times |

Both accessors (`selection`, `brush`) remain verified with real gestures from the prior pass; no regressions
found. No bugs found this pass (the two upstream bqplot items and the one shinywidgets cross-figure-selector
limitation from the prior pass's "Bugs found" are unaffected by the 33 new commits -- not re-verified this
pass since nothing in the changelog touches selectors spanning two figures).

Judgment call: kept `examples/01-16` and their screenshots as-is after re-reading each one's surrounding prose
against current docstrings/source; found nothing else stale.

## Update 2026-11-11 (B1 rename: selection() -> selected())

- The primary selection accessor was renamed to `selected()` (one rule across renderers; unreleased API, no
  shims). Guide, examples, and front matter updated; widget *trait* names (e.g. jscatter's `selection`,
  lonboard's layer `selected_index`, ipyaladin's `_selected_objects`) are unchanged, and references to those
  or to upstream widget methods (`plot.value.selection()`, `EmbeddingAtlasWidget.selection()`,
  `Aladin.selection()`) were deliberately left alone.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data`: no new example, no meaningful large-data story for bqplot (SVG/Canvas marks, no WebGL, no measured ceiling anywhere upstream or in this guide). Pointed to holoviews+datashader and jscatter as the siblings for scale, driven via this guide's own 'Coordinating multiple views' round-trip pattern.

## Update 2026-11-11 (B2: selected_rows(), bqplot)

- New accessor `plot.selected_rows(df, *, mark=None)`: the rows of `df` (required -- a bqplot figure retains
  no data frame; pandas/polars in, same type out) at one mark's selected positions. `mark=` is an index into
  `fig.marks` or the `Mark` object itself, omittable only for single-mark figures (otherwise a `ValueError`
  naming `mark=`). Empty frame while the mark has nothing selected. Implemented in the
  `b2-bqplot-selected-rows` worktree, stacked on `b2-jscatter-selected-rows` (PR pending).
- Front matter `accessors:` list, intro paragraph, and the accessor reference table all gained
  `selected_rows()`. New subsection "`selected_rows()`: the selection, as rows of your data frame" after
  `selected()` (documents `mark=` for multi-mark figures and the positional caveat); the guide no longer
  teaches `df.iloc[plot.selected()[0]]` anywhere for the rows use case.
- Examples switched from the hand-rolled `sel = plot.selected()[0]; df.iloc[...]` to
  `plot.selected_rows(df)`: `08_selection.py` (the detail grid), `13_linked_lasso_table.py` (lasso -> table),
  `14_linked_click_detail.py` (first row of the selection), `17_download_selection.py` (also retitled
  "Reading selected_rows() on demand"; x/y arrays became a `points` DataFrame), and both gallery apps
  (`template_brush_explorer.py` summary + table; `showcase_gapminder_explorer.py` summary + ranked bars --
  both now read `selected_rows(year_rows())`). `15_linked_brushing.py` keeps positions on purpose (the
  selection setter on the other figure's mark takes positions), as does `07_selectors.py`'s count.
- Cross-cutting articles updated: cheatsheet (new bqplot row), reacting-to-widgets "Rows of your data"
  (bqplot added to the list + a bullet), choosing-a-widget matrix (accessor count 2 -> 3), linked-views
  (the "Selection -> table of rows" list and the "third variant" paragraph now describe
  `selected_rows(df)` instead of plain positional indexing).

Verification (all against the B2 worktree's code, real gestures, screenshots looked at):

| File | Ran | Screenshot looked at | Gesture | Accessor confirmed |
|---|---|---|---|---|
| `examples/08_selection.py` | yes | yes (before/after re-shot) | click a point | `selected_rows(tips)` grid: 1 row (bill 17.92, tip 4.08) matching the red point's tooltip |
| `examples/13_linked_lasso_table.py` | yes | yes (before/after re-shot) | lasso path | `selected_rows(gap2007)` grid: 30 country rows ("Viewing rows 1 through 18 of 30") |
| `examples/14_linked_click_detail.py` | yes | yes (before/after re-shot) | click a point | detail card: "Sat Dinner, Party of 2, bill $17.92, Tip $4.08 (23%)" |
| `examples/17_download_selection.py` | yes | yes (before/after re-shot, new title) | brush drag + download click | CSV has `x,y` header + 120 data rows |
| `gallery/template_brush_explorer.py` | yes | yes (re-shot) | brush drag | summary "193 visits, avg bill $16.60, avg tip $2.73" + matching table |
| `gallery/showcase_gapminder_explorer.py` | yes | yes (before/after re-shot) | lasso path | summary "68 countries, 784M people"; ranked bars update in place (Japan, Germany, ...) |

No new bugs found. One driving note: `LassoSelector`'s `rect[pointer-events="all"]` overlay is
`visibility="hidden"`, so `to_be_visible` checks and overlay-sized drags fail for it -- size the lasso path
off `#<output> svg` instead (brush selectors' overlay is visible and works as before).
