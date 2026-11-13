# NOTES: ipydatagrid guide

## Versions

- ipydatagrid 1.4.0, bqscales 0.3.7, plotly 6.9.0, pandas 3.1.0, shiny 1.9.0, Python 3.12.
- shinywidgets: `main` at the time of writing (commit churned several times mid-session as other agents' PRs
  landed; verified `shinywidgets/_ipydatagrid.py` was byte-identical across the commits I touched, so none of the
  accessor semantics changed under me). Last checked against `00f90249` / `38a1796b`-era `main`.
- Date: 2026-10-30.
- Ran everything through an isolated worktree partway through (coordinator's instruction, after another session
  started switching branches in the shared main checkout), at
  `/private/tmp/claude-502/-Users-cpsievert-github-py-shinywidgets/b5f9c833-cf3f-448f-841f-2c46c3116629/scratchpad/main-wt`.
  Confirmed `shinywidgets/_ipydatagrid.py` was identical there before relying on it.

## Verification table

Every file was run with `shiny run` and driven with Playwright Chromium (headless, default launch args -- no
WebGL/swiftshader flags needed; ipydatagrid is canvas-2D, not WebGL).

| File | Ran | Screenshot(s) | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | before/after | click + shift-click rows | `selected()`, `visible_data()` |
| `examples/02_renderers.py` | yes | 1 | none (static feature tour) | n/a |
| `examples/03_streaming_large_grid.py` | yes | 1 | click (for the Gotchas repro; see below) | n/a (no accessors used in the example itself) |
| `examples/04_selection_modes.py` | yes | cell mode, row mode | drag (cell), click (row), mode switch | `selected()`, `visible_data()` |
| `examples/05_clicked_cell.py` | yes | before/after | click | `clicked_cell()` |
| `examples/06_edited_cell.py` | yes | before/after | double-click, type, Enter | `edited_cell()` |
| `examples/07_visible_data.py` | yes | before/after | header-menu filter (`region = North`) | `visible_data()` |
| `examples/08_rate_limiting.py` | yes | 1 | 4 distinct-row clicks, timed | `selected()` vs. `reactive_read()` contrast |
| `examples/09_update_in_place.py` | yes | before/after | 3 button clicks (highlight/sort/replace) | `selected()` (via Python-side `.selections =` write) |
| `examples/10_sizing.py` | yes | 1 | none (static layout comparison) | n/a |
| `gallery/template_spreadsheet.py` | yes | 1 | double-click edit + drag | `selected()`, `visible_data()`, `edited_cell()` |
| `gallery/showcase_monthly_sales.py` | yes | before/after-drag/after-edit | drag + double-click edit | `selected()`, `visible_data()`, `edited_cell()` |

Sort-driven `visible_data()` (as opposed to the filter I drove myself) and the zero-match-filter case are not
re-driven by me in this pass; they're covered by the existing, already-committed
`tests/playwright/ipydatagrid_accessors/test_ipydatagrid_accessors.py`
(`test_visible_data_follows_sort_and_filter`, `test_visible_data_returns_no_rows_for_a_zero_match_filter`), which
I read but did not re-run. Treat those two as "verified via the existing suite," not "verified by me this
session."

### Accessor coverage (for the coordinator)

- `selected()` -- verified with a real gesture (click, shift-click, drag, mode switch). Yes.
- `clicked_cell()` -- verified with a real gesture (click, including `selection_mode="none"`). Yes.
- `edited_cell()` -- verified with a real gesture (double-click edit, Python `set_cell_value_by_index`). Yes.
- `visible_data()` -- verified with a real gesture (header-menu filter). Yes (sort and zero-match-filter paths
  verified via the existing committed test suite, not re-driven by me).

## Bugs found

### shinywidgets (none found this pass)

I did not find a shinywidgets-side bug in `render_ipydatagrid` or `_ipydatagrid.py` on current `main`. The
should-fix items from the old PR report (`docs/widget-reports/ipydatagrid/report.md`: `GeoDataFrame` rejection,
the example's misleading "click a header to sort" copy, the missing `selection_mode` default) are all already
fixed on `main` -- confirmed by reading `is_pandas_dataframe()`'s MRO walk, the current `examples/ipydatagrid/app.py`
copy, and the accessor docstrings, and by using `GeoDataFrame`-shaped column widths/renderers without issue in my
own examples.

### Upstream (ipydatagrid / bqscales)

1. **`StreamingDataGrid` throws on cell click** -- re-verified on current main (ipydatagrid 1.4.0): clicking a
   body cell raises `TypeError: Cannot read properties of undefined (reading '1') at getDatasetRowFromView`,
   exactly as the old report found. Long-standing limitation, not a regression. Repro:
   `docs/widget-guides/ipydatagrid/examples/03_streaming_large_grid.py`, click any body cell.
2. **`select()`/`clear_selection()` mutate in place and don't notify** -- re-verified. Long-standing. Documented
   in the guide's Gotchas and the `updating from Python` section with the `.selections = [...]` workaround.
3. **A Python-side `set_cell_value_by_index()` write echoes back through `edited_cell()`** -- re-verified.
   Long-standing. Guarded against in both `examples/06_edited_cell.py` and the showcase gallery app.
4. **`BarRenderer()` with no `bar_value` draws nothing** (`bar_value` defaults to a scale with `max=0.0`, not an
   auto-scaling `None`) -- re-verified. Long-standing.
5. **`bqscales` scale traits reject numpy scalars.** `LinearScale(min=0, max=df["x"].max())` raises
   `TypeError: ... expected a float, not an int64 np.int64(...)`. This one isn't in the old report -- it's new to
   this pass (the old report's gallery app used `int(df["total"].max() * 1.2)`, which happens to produce a plain
   Python `int` and sidesteps the issue; my first draft of `examples/02_renderers.py` used `.max()` directly and
   hit it). Worth flagging upstream: a `Float`-typed traitlets trait that doesn't accept numpy's own float type is
   a sharp edge for anyone building a scale from a pandas column.
6. **A heavy companion re-render can interrupt an in-progress cell-selection drag** (new finding, not in the old
   report). `selections` streams continuously while the user drags a selection rectangle, not just once at
   mouse-up. I built the showcase gallery app's side chart as a `render_plotly` output that rebuilt a fresh
   `go.Figure` from `grid.selected()` + `grid.visible_data()` on every change; dragging a block then
   consistently collapsed to just the starting cell, with no browser console error. Isolated to the companion
   chart specifically (confirmed with a series of minimal repros in scratch: the same grid + renderers +
   `editable=True`, with or without the companion render, drags correctly; adding the per-tick `go.Figure` rebuild
   is what breaks it). Root cause is presumably the plotly rebuild stalling the main thread long enough that the
   browser drops its drag/pointer-capture state before the next `mousemove`. Fixed in the showcase by building the
   `FigureWidget` once and updating `.data[i].y`/`.data[i].visible` in place from a `@reactive.effect`, which does
   not reproduce the problem. I'm treating this as an upstream/browser-interaction issue (Lumino's canvas drag
   tracking being sensitive to a stalled main thread) rather than a shinywidgets bug, since shinywidgets isn't
   doing anything unusual in the message path -- but it's a real trap for anyone pairing a `selected()`-driven
   companion view with a live drag, and it's worth being loud about in the guide (I added a Gotchas bullet and a
   paragraph under Rate limiting, since the natural first fix -- "just throttle it" -- doesn't work; see next
   item).
7. **MultiIndex row-header groups go stale after a sort** -- not re-verified this pass (I didn't build a
   MultiIndex example; the old report's repro still looks structurally sound and reproduces in ipydatagrid's own
   static export per that report, independent of shinywidgets). Carried forward as a known limitation; every
   example in this guide uses flat key columns specifically to avoid it.

### Docs / design-doc (per the coordinator's amendment)

8. **The reactive-accessors plan doc's claim that ipydatagrid `selected()` has "no [rate limit] (gesture reports
   at gesture end)" is wrong.** (`docs/plans/2026-10-29-reactive-accessors-plan-7-second-pass.md`, the accessor
   summary table.) It streams during the drag, as finding 6 above demonstrates concretely. The actual code
   (`_ipydatagrid.py`, `_render_widget.py`) never makes this claim itself -- it's specific to the planning
   document's summary table -- but since the coordinator asked us to verify claims in the design/plan docs too,
   flagging it here. The accessor's own docstring (`.selected()`) is accurate: it just says "not rate-limited,"
   which is true and doesn't claim anything about *when* it fires.
9. **`rate_policy`/`rate_delay` on `@render_ipydatagrid(...)` silently do nothing for any of the four accessors.**
   Not exactly wrong documentation (the docstring's Parameters section describes the kwargs accurately and
   generically, matching every other renderer), but it's an easy trap: a user who reads "how do you rate-limit
   `.selected()`?" and finds these kwargs will reasonably assume they work, and nothing in the renderer raises
   or warns when they don't apply (because `AccessorSpec.rate_policy` is `None` for every ipydatagrid accessor, so
   the per-accessor limiter is never constructed -- see `shinywidgets/_accessors.py`, `Accessors.__init__`). I
   verified this by reading the `Accessors.__init__` construction logic and with a quick unit-style script
   (`/private/tmp/.../scratchpad/agents/ipydatagrid/test_rate_probe.py` -- not committed anywhere) showing
   `slot.limiter is None` even when `rate_policy="throttle"` is passed to the renderer. I documented this
   explicitly in the guide's Rate limiting section rather than letting a reader find out the hard way. This isn't
   ipydatagrid-specific -- it'll be true of any renderer whose `AccessorSpec`s don't declare a default
   `rate_policy` -- so it may be worth a one-line mention in the shared accessor docs/design doc, but I didn't
   check every other renderer's specs to confirm how common it is.

## Judgment calls

- **Datasets: only the quickstart uses a real public dataset** (`plotly.express.data.tips()`), per the
  coordinator's mid-session note to prefer real data for hero/quickstart/gallery "where possible." I judged the
  cost/benefit differently for the rest:
  - The feature-tour examples (`02`-`10`) are each isolated around one specific interaction (a renderer, a
    selection mode, a sizing comparison); a synthetic, clearly-labeled dataset keeps the numbers small and
    legible in a cropped screenshot, which a real dataset with messier distributions would work against. Swapping
    all of them would have meant re-deriving plausible column semantics and re-verifying every screenshot, for a
    guide whose point is the *interaction*, not the data.
  - The showcase gallery app's "Monthly sales" narrative is itself the point (it's what the old report's agent
    proposed, and the assignment brief's own section list assumes a sales-shaped example); there's no equally
    natural public dataset for "12 region/product rows, editable monthly figures" that wouldn't have required
    reshaping something real into that exact shape, at which point it stops being more "real" than a clearly
    synthetic business example.
  - The template gallery app is explicitly "swap in your own DataFrame" -- generic synthetic numbers avoid
    implying any particular real-world meaning the user would need to un-learn.
  - Happy to revisit any of these if the maintainer disagrees; swapping `03`/`04`/`07`'s data for something like
    `plotly.express.data.gapminder()` / `stocks()` wouldn't be hard if the website wants more "real" flavor
    throughout.
- **Gallery headers are `#` comments, not docstrings.** Caught this myself (Shiny Express auto-displays a leading
  module docstring as visible page text -- confirmed with a 4-line repro) before the coordinator's note on the
  same issue arrived; both gallery files use a comment block instead, with a one-line note explaining why.
- **The showcase's companion chart ended up non-trivially different from a first draft** (see finding 6): what
  started as "rebuild a `go.Figure` per selection change" (simple, matches the `07_visible_data.py` pattern) had
  to become "build a `FigureWidget` once, update traces in place" specifically because of the live-drag
  interaction. I'd like a second opinion on whether this nuance (some companion-view updates are safe to rebuild,
  others -- specifically ones driven by a value that streams mid-gesture -- need to be in-place) is explained
  clearly enough in the guide, or whether it needs its own callout box rather than living inside "Rate limiting."
- **Pixel-coordinate gestures are brittle by construction** (same caveat as the existing committed Playwright
  tests' own comments): every `page.mouse.click`/`drag` in my verification scripts hardcodes column pixel offsets
  for ipydatagrid 1.4.0's lumino defaults (`base_row_size`/`base_column_header_size` = 20, `base_column_size`/
  `base_row_header_size` = 64). These aren't committed as tests, just scratch verification scripts, so this is a
  one-time cost, not an ongoing maintenance burden -- flagging only so the maintainer knows the screenshots were
  produced this way.

## Editor's notes for the website

- **Strongest material:** the `edited_cell()` → in-place `plotly` chart update
  (`examples/06_edited_cell.py`) and the showcase gallery app are the best demonstrations of what makes
  this renderer worth having -- they show the accessor, the recompute-and-guard pattern, and the in-place update
  philosophy all at once, with a screenshot that's immediately legible (a bar visibly growing, a trend line
  visibly updating).
- **Second strongest:** the renderers feature tour (`02_renderers.py`) -- the heatmap/bar/conditional-color
  screenshot is the single most "this is cool" image in the set and would make a good hero or near-hero image if
  the maintainer prefers a visually richer hero over the plainer quickstart table.
- **Cut candidates for a shorter page:** `08_rate_limiting.py` and its section are the most "inside baseball" of
  the bunch -- valuable for someone debugging unexpected accessor behavior, but skippable for a first read. If the
  page needs trimming, fold its one-paragraph conclusion ("accessors aren't rate-limited; only `reactive_read()`
  is") into the accessor reference table's footnote and drop the worked example.
- `10_sizing.py` is useful but visually underwhelming (two mostly-empty-looking grids); consider pairing it with
  `03_streaming_large_grid.py`'s screenshot instead of giving it a full section, since both are really one point
  ("sizing is manual; verify before shipping a wide table").

## Cross-widget pairings (for the coordinator's cross-cutting articles)

- pairs with: plotly (`06_edited_cell.py`, `07_visible_data.py`, and the showcase gallery app all drive
  a `render_plotly` companion chart from ipydatagrid accessors; the showcase additionally demonstrates the
  in-place-vs-rebuild distinction that's specific to a live-drag-driven value)

## Dropped from the old report, and why

- **The MultiIndex repro and its two before/after screenshots** -- still true (see Bugs found #7), but not worth
  re-building a MultiIndex example just to re-screenshot a known, unfixable upstream issue; one guide sentence
  plus a pointer to the old report's evidence does the job.
- **The large-data benchmark table** (10k/100k/1M rows × DataGrid/StreamingDataGrid/`render.DataGrid`, with exact
  timings and websocket byte counts) -- kept the qualitative conclusion ("StreamingDataGrid sends only the visible
  window; plain DataGrid ships the whole frame") and one measured number (200k rows, 1.3s to first paint, this
  session), but dropped the full cross-renderer comparison matrix: it's a `render.DataGrid`-vs-ipydatagrid
  competitive comparison more suited to a "choosing a widget" cross-cutting article than this guide, and exact
  timings from a shared, loaded machine aren't reproducible numbers worth enshrining in a guide.
- **The theming/dark-mode investigation's "setting `document.body.dataset.jpThemeLight`" workaround detail** --
  mentioned that the palette is chosen once from JupyterLab-only attributes, but dropped the live-toggle
  workaround recipe (the old report itself flagged it as unverified, and it's a hack users would need to
  re-discover themselves anyway, not something to present as a supported pattern).
- **The PR-review material** (merge conflicts, should-fix list, scorecard, open questions for the maintainer) --
  entirely superseded; all of it either already landed on `main` or was specific to a PR that no longer exists in
  that form.
- **The polars/pyarrow/Series "unhelpful error message" finding** -- re-confirmed the behavior still holds (only
  pandas is coerced) but compressed it to one Gotchas bullet rather than a full finding with a proposed error
  message, since it's a minor DX paper cut rather than something blocking a user.

## Update 2026-11-11 (main @ 32ca7035)

Versions: ipydatagrid 1.4.0, bqscales 0.3.7, plotly 6.9.0, pandas 3.1.1, shiny 1.9.0, shinywidgets
0.8.2.post1.dev135+g32ca7035 (editable install from the worktree at `32ca7035`). Worktree:
`/private/tmp/claude-502/-Users-cpsievert-github-py-shinywidgets/ce388f54-2d12-4580-8021-8300841b1d00/scratchpad/main-wt`.
Ports used: 8306-8309 (assigned range 8300-8399).

### What changed in the guide, and why

- **#441 renames were already applied** before this pass started (`cell_clicked()` -> `clicked_cell()`; `edited_cell()`
  keeps its name -- #441 only renamed `cell_clicked`). Confirmed by grep: no method-name occurrences of
  `cell_clicked()` remained anywhere in `guide.md`, `examples/`, or `gallery/`. Only a stale screenshot filename
  (`05_cell_clicked_before.webp`) still used the old wording; left as-is (asset path, not user-visible API).
- **#400: `selected()` now debounces by default (0.25s).** This is the single biggest factual correction in
  this pass. The old guide's accessor reference table said "None -- see Rate limiting" and the Rate limiting
  section's entire thesis was "none of ipydatagrid's four accessors declare a default rate policy, so
  `rate_policy`/`rate_delay` have no effect on them." Both claims are now false for `selected()`. Verified
  directly with a real drag gesture (see below): a 9-row drag published `selected()` exactly twice (seed +
  one debounced value after the drag settled) vs. 10 times for the un-rate-limited `reactive_read()` equivalent.
  Also verified the **direction flipped**: previously `rate_policy`/`rate_delay` only governed `reactive_read()`
  and never the accessor; now the kwargs govern *both* uniformly, overriding the accessor's own debounce default
  (verified: `rate_policy="throttle", rate_delay=1.0` made `selected()` and `reactive_read()` fire identically,
  3 times each, for the same drag).
- **Re-checked the "heavy companion rebuild interrupts a drag" Gotcha and softened it.** The 2026-10-30 pass found
  and carefully documented a real repro: rebuilding a `go.Figure` from scratch on every `selected()` tick
  stalled the browser's main thread enough to drop pointer capture mid-drag, collapsing the selection. I could
  **not reproduce this in this pass**, with the new default debounce *or* with `rate_delay=0` (replicating the
  old no-rate-limit behavior) against both a small (30-row) and a large (2000-row) companion rebuild, each time
  with a slow multi-step synthetic drag -- the selection always completed intact. I don't know whether this means
  the bug is gone, was specific to the previous agent's exact repro conditions (a real headed/interactive session
  vs. my headless Playwright run, or a more complex production chart), or is just flaky under load on a shared
  machine. What I can say confidently: with the new default debounce, `selected()` **does not fire at all
  during a drag** (only once, after it settles), which removes the specific trigger the old finding described
  (a heavy rebuild racing *live* pointer movement). I rewrote the Gotcha to recommend in-place updates as
  still-good-practice (avoids a full re-render and a visible flash) rather than as "required to prevent a
  crash," and rewrote the matching comment in `gallery/showcase_monthly_sales.py`'s `profile()` function the same
  way. Flagging as a judgment call the maintainer may want a second opinion on -- see "Bugs found" below.
- **Applied #437's kept/re-seeded distinction throughout.** `selected()` and `visible_data()` describe the
  grid's own current state and **re-seed** from the new grid at every render (confirmed:
  `tests/unit/test_ipydatagrid_accessors.py::test_selections_attach_seeds_and_emits` shows the attach emits a
  fresh seed immediately). `clicked_cell()`/`edited_cell()` describe something the user did and **keep** their
  value across a re-render (confirmed: `tests/unit/test_ipydatagrid_accessors.py::test_click_accessors_are_retained`
  asserts both are `kind="state"`). The old guide's "event vs. state accessor" framing and "`clicked_cell()`
  resets to `None` on every re-render" claim are both gone.
- **Added "Reading an accessor on demand"** (new example `11_read_on_demand.py`): a download-button handler reads
  `selected()`/`visible_data()` with nothing ever displaying them reactively first.
- **Rewrote `examples/08_rate_limiting.py` and its section from scratch** to demonstrate the new (and inverted)
  behavior rather than the old "the accessor ignores `rate_policy` entirely" claim.
- Front matter `accessors:` list unchanged (`[selections, clicked_cell, edited_cell, visible_data]` -- no names
  changed, no accessors added this cycle for this renderer).

### New/edited examples -- verification status

| file | ran | gesture | accessor confirmed | screenshot(s) looked at |
|---|---|---|---|---|
| `examples/08_rate_limiting.py` (rewritten) | yes | an 8-step, ~0.7s synthetic drag across 9 rows | `selected()` fired twice (seed + one debounced publish); `reactive_read(grid.widget, "selections")` fired 10 times (once per raw move) on the exact same gesture | `08_rate_limiting.webp` (replaced; now shows the new counts, "2" / "10") |
| `examples/11_read_on_demand.py` (new) | yes | row-header click + shift-click to extend to a 4-row block, then click "Download selected rows" | `selected()`/`visible_data()` read inside a `@render.download_button` handler never displayed reactively; downloaded CSV's 4 rows matched the visually selected block exactly | `11_read_on_demand_before.webp` (new), `11_read_on_demand_download.webp` (new, via `file://` navigation to the downloaded file) |
| `gallery/showcase_monthly_sales.py` (edited: comment only, no code change) | yes | an 8-step drag across the `region` column | No regression: status bar and in-place chart update correctly with the new debounce; no console errors beyond unrelated 404s (favicon/static assets) | `showcase_after_drag.webp` (scratch only, not added to `guide.md` -- no visual change, comment-only edit) |
| `examples/09_update_in_place.py` (unedited, spot-checked since its claims are adjacent to the debounce change) | yes | 2 button clicks (Highlight, Sort) | `.selected()` still updates correctly through the in-place `.widget.selections = [...]` write path, now with up-to-250ms latency (invisible at the example's normal interaction pace) | not re-screenshotted (no code or prose change to this example) |

Accessor coverage this pass: `selected()` -- re-verified with a real drag gesture under both the default and an
explicit `rate_policy` (the central factual fix this pass addresses). `clicked_cell()`, `edited_cell()` --
unchanged gesture/payload, only their across-re-render semantics changed (now "kept" instead of "event"),
confirmed via the existing unit test rather than re-driven in a browser (nothing about the click/edit gesture
itself changed). `visible_data()` -- unchanged gesture, re-seed semantics confirmed via the existing unit test
(`test_visible_data_accessor` family).

### Items from the old "Bugs found" now fixed / now obsolete

- Finding 6 ("a heavy companion re-render can interrupt an in-progress drag") and finding 8 (the design doc's
  stale claim that `selected()` has "no rate limit") are both **superseded by #400**: the accessor now has a
  real default debounce. See the detailed discussion above -- I could not re-reproduce finding 6's specific
  browser-interruption symptom this pass, so I'm not marking it definitively "fixed," but the mechanism that
  triggered it (continuous unthrottled firing during a live drag) is gone by default.
- Finding 9 ("`rate_policy`/`rate_delay` silently do nothing for any of the four accessors") is **fixed for
  `selected()`** by #400 and otherwise moot: `clicked_cell()`/`edited_cell()`/`visible_data()` still have no
  default rate policy of their own (nothing to rate-limit for discrete events or an already-debounced-by-proxy
  trigger), which is accurate current behavior, not a bug.
- Findings 1-5, 7 (StreamingDataGrid click crash, `select()`/`clear_selection()` not notifying, edit echo,
  `BarRenderer()` default, numpy scalar rejection, MultiIndex staleness) are unrelated to the accessor redesign
  and not re-verified this pass.

### New bugs found (2026-11-11)

None found this pass beyond the unresolved question noted above (could not reproduce the pre-#400 drag-interrupt
finding, in either direction -- not confident enough to call it fixed or still-present).

## Update 2026-11-11 (B1 rename: selections() -> selected())

- The primary selection accessor was renamed to `selected()` (one rule across renderers; unreleased API, no
  shims). Guide, examples, and front matter updated; widget *trait* names (e.g. jscatter's `selection`,
  lonboard's layer `selected_index`, ipyaladin's `_selected_objects`) are unchanged, and references to those
  or to upstream widget methods (`plot.value.selection()`, `EmbeddingAtlasWidget.selection()`,
  `Aladin.selection()`) were deliberately left alone.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example -- reused this guide's existing StreamingDataGrid vs. DataGrid distinction (already in the introduction and the streaming example) rather than resurrecting the dropped 10k/100k/1M-row benchmark table noted in this guide's own NOTES.
