# NOTES: itables guide

Versions: itables 2.9.1, shiny 1.9.0, plotly 6.9.0, pandas 3.1.0, polars 2.0.0, pyarrow 26.0.0.
shinywidgets commit: `f8238de6` (main, 2026-10-30). Date: 2026-10-30.

Note: the main checkout is shared by many agents right now, and I twice hit a window where
`pyproject.toml` / `shinywidgets/_render_widget.py` had live, unresolved git-merge-conflict markers
(someone else's merge in progress on the shared checkout) which broke `uv run` and `import shinywidgets`
for a couple of minutes. Both resolved on their own; not a shinywidgets bug, just a shared-machine hazard.
Mentioning in case other agents hit the same thing and wonder if they broke something.

## Verification table

All apps run via `uv run --no-sync shiny run`, driven with Playwright (Chromium headless, 1280x800,
`device_scale_factor=2`), screenshots read back with the Read tool before referencing them.

| File | Ran | Screenshot | Gesture driven | Notes |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes | click row | |
| examples/02_search_and_filters.py | yes | yes | type into column filter | |
| examples/03_search_panes.py | yes | yes (before/after) | click a SearchPane value | |
| examples/04_buttons_export.py | yes | yes | n/a (buttons not clicked; triggers a real file download) | |
| examples/05_styling.py | yes | yes | n/a (visual only) | found + fixed a real bug in my own `createdCell` snippet, see Bugs below |
| examples/06_pandas_styler.py | yes | yes | n/a (visual only) | |
| examples/07_polars.py | yes | yes | click + ctrl-click rows | confirms polars indexing of `selected_rows()` |
| examples/08_selected_rows_accessor.py | yes | yes (before/after) | click, ctrl-click, sort, click | accessor **verified**: position survives sort |
| examples/09_rate_limiting.py | yes | yes (during/after) | 4 rapid ctrl-clicks | confirms accessor is never rate-limited; `reactive_read()` debounce is separate, see Bugs |
| examples/10_programmatic_selection.py | yes | yes (before/after) | button click | Python-set selection verified in browser |
| examples/11_selection_updates_plot.py | yes | yes (before/after) | click + 2x ctrl-click | cross-widget: itables -> plotly |
| examples/12_selection_detail_card.py | yes | yes (before/after) | click row | |
| examples/13_update_in_place.py | yes | yes (before/after) | button click | confirms `update()` keeps `buttons`, pandas index shown |
| examples/14_filter_preserves_selection.py | yes | yes (before/after) | 2x click + select_option | found + fixed a real selection-remap bug, see Bugs |
| gallery/template_table_as_input.py | yes | yes (before/after) | click + ctrl-click | |
| gallery/showcase_gapminder_dashboard.py | yes | yes (3 shots) | click + ctrl-click + select_option | combines accessor, cross-widget plot update, and filter remap |

Accessor coverage: `selected_rows()` is the only accessor (`shinywidgets._itables.ITABLES_ACCESSORS`), verified
with real clicks/ctrl-clicks/sorts in 7 of the apps above.

## Bugs found

**In my own example code (not shinywidgets or itables), but worth flagging loudly:**

- A bare `@reactive.effect` that reads a `reactive.Value` and `.set()`s it from its own current value
  (`count.set(count() + 1)`, no `reactive.isolate()`) self-invalidates forever. In my first draft of
  `09_rate_limiting.py` this didn't just spin that one effect -- it silently froze the **entire app**,
  including the itables output's first render, with zero console errors and zero server-side traceback.
  `curl` against the running server still returned 200 (the static HTML shell), but the websocket session
  never got far enough to send the table's initial comm-open message. I only found it by bisecting down to a
  no-op effect with nothing itables-related in it at all. Fixed with `with reactive.isolate(): count.set(...)`.
  **Flagging for the coordinator:** `docs/widget-guides/ipyleaflet/examples/09_rate_limiting.py` (seen while
  reading sibling guides for conventions) has the identical `count.set(count() + 1)` pattern with no isolate.
  I did not test that file -- it may be fine if nothing else in that app ever hangs a flush long enough to
  notice, but given how silently and completely this fails, it's worth a 30-second check.
- `examples/14_filter_preserves_selection.py` (and the showcase, before I fixed it) initially re-indexed the
  "still selected" output as `countries.iloc[table.selected_rows()]` -- using the *original, unfiltered* frame
  with positions that are only valid against the *currently shown* (filtered) frame. After filtering to Europe,
  the panel showed "Afghanistan" (Asia, position 0 of the original frame) instead of "Albania". Fixed by
  tracking the currently-shown frame in a `reactive.value` and indexing that instead. This is the kind of bug
  a user would actually hit with this exact pattern, so I think it's worth the guide explicitly warning about
  it (now does, in "Updating the widget from Python" and the filter-preserves-selection pattern).

**Upstream itables (verified on 2.9.1, long-standing, not regressions):**

- A `columnDefs` entry's `createdCell` callback receives itables' internal `[display_string, raw_number]` pair
  for a numeric column that has no `render` of its own -- not a plain number. `data < 60` is always false
  (array coerces to its joined string, `Number()` of a 2-element array is `NaN`). Columns that *do* have a
  custom `render` are unaffected (their callback gets the plain value). I hit this live while writing the
  styling example (the life-expectancy coloring silently did nothing until I added `Array.isArray(data) ? data[1] : data`). Not documented anywhere I found in itables' own docs.
- `ITable.update(df)` drops `columnDefs`, `buttons`, and similar options unless they're passed again in the
  same `.update()` call. Matches the old report's finding; still true.
- The `caption` passed to `ITable(df, caption=...)` at construction never appears in the initial HTML (the
  trait-change observer that would render it fires after the table's HTML is already built). Only
  `.update(caption=...)` after the fact shows it. Matches the old report's finding; still true.
- `footer=True` combined with `column_filters="header"` renders a table with the header filter row intact but
  **every data cell empty**, with the column names duplicated into the footer row instead of per-column
  summaries. Verified with a 2-column, 3-row pure repro (`countries`/gapminder not needed). Matches the old
  report's finding; still true.

**Shinywidgets, confirmed fixed since the old PR-era report (`docs/widget-reports/itables/report.md`) -- not
current bugs, noted here only so nobody re-chases them:**

- itables' bundled jQuery no longer clobbers the page's global `$` (verified: bslib card resize, full-screen
  toggle, `ui.input_dark_mode()`, and a page script registering `$.fn.myPlugin` before itables loads all still
  work; `tests/playwright/render_itables_edge/` has a full suite for this).
- `$.fn.dataTable.render.number(...)`-style JS option recipes that need DataTables' own jQuery plugin now work
  (there's a compatibility shim; verified with the exact itables-docs recipe).
- Dark mode (`ui.input_dark_mode()`) is legible; a CSS rule maps itables' theme variables onto Bootstrap's.
- `ITable` subclasses get the same fill defaults as the base class (MRO-based dispatch).

**Still a real, current limitation (not a regression, not newly introduced; matches the old report):**

- Small containers collapse the usable row area. Verified with a plain 2-column table: at `height="200px"`,
  the search box and footer/pagination eat nearly the whole budget and the scrolling body gets ~1 visible row
  (mostly clipped); at `height="350px"` there's room for about 5 rows before scrolling. The existing docstring
  guidance ("give it roughly 350px or more") is accurate -- I verified it rather than just repeating it.

## Judgment calls

- Used `plotly.express.data.gapminder()` (filtered to 2007, 142 rows) as the one dataset across every example
  and the gallery, instead of a different synthetic dataset per section. It's real, recognizable, has a mix of
  categorical/numeric columns worth filtering and formatting, and keeping it constant makes the guide's running
  example easier to follow across sections. Happy to vary it if the maintainer prefers more dataset diversity
  for visual variety on the page.
- Dropped the `select PendingDeprecationWarning`-style "non-issues" list from the old report (import-time
  construction errors, Styler-without-allow_html's error message, `pl.from_pandas` needing pyarrow) -- these
  are expected, self-explanatory errors, not things a reader needs taught.
- Did not add a dedicated example for `column_filters="row"` (the alternative to `"header"`) or RowGroup/
  FixedColumns/KeyTable extensions -- the "What you can build" section already covers 6 highlights and the
  brief says section counts are targets, not quotas. Mentioned RowGroup/FixedColumns/KeyTable only in the
  comparison table and "Learn more" link.
- The showcase's `current_rows` / selection-remap-by-key pattern is genuinely a bit fiddly (three reactive
  pieces: the tracked current frame, the remap, and the in-place `.update()`). I kept it because it's the single
  most valuable thing in this guide (the brief calls out exactly this kind of pattern as the most valuable part
  of each guide), but a reader skimming might want this called out as "the advanced pattern" rather than
  something to reach for by default. Worth a pull-quote or callout box on the website if that's easy to do.
- `04_buttons_export.py`'s Copy/CSV buttons were not actually clicked by Playwright (clipboard/download side
  effects are awkward to assert in a headless run and not worth the added test complexity for a static
  screenshot). Verified instead that the buttons render and are wired to a real DataTable instance (same
  mechanism verified end-to-end in `tests/playwright/render_itables_edge/test_render_itables_edge.py`'s
  `$('#formatted table.dataTable').DataTable()` check).

## Pairs with

- **plotly** -- `examples/11_selection_updates_plot.py` and the showcase: table selection drives an in-place
  `go.FigureWidget` update (point highlight color/size), no re-render.
- Any table-like sibling (**reactable**, **ipydatagrid**, **perspective**) would make a reasonable "pick your
  table" comparison page; the "`@render_itables` vs. `render.data_frame`" section here only compares against
  Shiny's own table outputs, not the other widget tables.

## Editor's notes for the website

- Strongest sections: "Coordinating multiple views" (all three patterns are short, concrete, and screenshotted
  before/after) and the Rate limiting subsection (the dual-counter screenshot makes an otherwise abstract
  distinction -- accessor vs. `reactive_read()` -- immediately legible).
- The feature tour (6 highlights) is solid but the longest section; if the page needs to shrink, cut SearchPanes
  first (buttons and column filters cover the "discoverability" point well enough on their own) or compress
  pandas-Styler and polars into a single combined "data in, as-is" subsection.
- The comparison table (`@render_itables` vs. `render.data_frame`) is short and, I think, load-bearing for
  someone choosing between the two -- would keep it even in a trimmed page.
- Hero image: used the showcase's "after" screenshot (filtered to Europe, one point highlighted red on the
  plot) since it shows the table, the cross-widget link, and the filter all in one frame. The plain quickstart
  screenshot is a safer, calmer alternative if the hero needs to look less busy.

## Dropped from the old report (`docs/widget-reports/itables/report.md`)

- The whole "PR review" framing (blockers/should-fix/nits, merge-readiness verdict, scorecard) -- that report
  was reviewing an unmerged PR; all of its shinywidgets-side blockers and should-fixes are fixed on main now
  (see "Bugs found" above for the ones I re-verified as fixed).
- The `.dt-scroll-body { min-height: ... }` CSS-floor prototype discussion -- speculative, not merged, and the
  current (also imperfect) behavior is simple to describe and verify instead (this guide's Layout section does).
- The "silent downsampling" / `maxBytes` deep dive (positions survive downsampling, 100k-row timing numbers) --
  kept the one-line mention in Gotchas; the detailed benchmarking isn't teaching material for a reader deciding
  whether to use this widget.
- Nits about the `ImportError` wording and `_as_widget` typing on non-ITable widgets -- implementation detail,
  not user-facing.

## Update 2026-11-11 (main @ 32ca7035)

### What changed and why

- **Accessor reference table reformatted** to the update brief's required columns (`returns | before any
  interaction | across re-render | default rate policy`), replacing the pre-redesign `fires when | None/empty
  means | default rate policy` columns. Matches the format other agents already landed in `plotly/guide.md`,
  `bokeh/guide.md`, and `panel/guide.md`.
- **`selected_rows()` re-render semantics made explicit and verified.** Per #437, every accessor is either
  "kept" (describes something the user did, carried across a re-render) or "re-seeded" (describes the widget's
  own current state, refreshed from the new widget at every render). Checked `shinywidgets/_itables.py`'s
  `attach_selected_rows`: it calls `emit(widget.selected_rows)` synchronously at attach, every render -- so
  itables' `selected_rows()` is **re-seeded**, not kept. Verified with a real browser gesture: selected two rows,
  clicked a button that forces the render function to re-run (a fresh `ITable(countries, select=True)`),
  confirmed `selected_rows()` reset to `[]` (probe app and script kept in this agent's scratch dir, not part of
  the guide's assigned directory). This matters because it means the *only* stale-position risk is the
  `.widget.update(df)` in-place path (old positions carry over unchanged into new data), not a full re-render
  (which always starts the new widget's own, usually-empty, selection) -- the `selected_rows()` subsection in
  `guide.md` now states both cases explicitly and points at the existing filter-preserves-selection pattern
  (`examples/14_filter_preserves_selection.py`) for the ID-keyed remap technique, per the update brief's note
  that positional indices into replaceable data are exactly the case to warn about.
- **New example, `examples/15_export_selected.py`** ("Read on demand: export selected rows"): a
  `@render.download_button` handler reads `table.selected_rows()` cold, at click time, with no other reader of
  that accessor anywhere in the app. Demonstrates the redesign's headline read-on-demand capability. Added as a
  new subsection in "Reacting to user interaction", between `selected_rows()` and "Beyond the accessors:
  reactive_read".
- **"Beyond the accessors: reactive_read" subsection updated** to mention `table.read("selected_rows")` as
  equivalent to `table.selected_rows()`, per #437's new `.read()` API and the update brief's narrative (tier 2:
  `.read()` replaces `reactive_read()` as the taught fallback for the output's own traits). Left the "Rate
  limiting" section's `reactive_read(table.widget, "selected_rows")` example untouched -- that one deliberately
  contrasts the accessor's no-rate-limit behavior against `reactive_read()`'s renderer-level rate policy, which
  `.read()` on an already-declared accessor name wouldn't demonstrate (it dispatches straight to the accessor,
  same as calling the method).

### Re-verification

| File | Gesture | Confirmed |
|---|---|---|
| `examples/15_export_selected.py` (new) | clicked Albania, Ctrl/Cmd-clicked Argentina, clicked download | downloaded CSV contained exactly Albania and Argentina's rows, read via the handler at click time |
| (ad hoc, scratch-only) re-render reseed probe | selected rows 1 and 3, clicked a re-render button | `selected_rows()` showed `[1, 3]` before, `[]` immediately after re-render |

Did not re-run examples 01-14 or the gallery apps in this pass: nothing in the 33-commit update changed
itables-specific code (`shinywidgets/_itables.py` is untouched in the diff since 2026-10-30), and none of the
guide's existing claims needed correction beyond the table format and the re-render/update() distinction above.
Their 2026-10-30 verification status in the table above this section stands.

### New bugs found this pass

None. `shinywidgets/_itables.py` and `render_itables`'s accessor behavior are unaffected by the 33-commit update
(itables was never part of the state/event split the redesign removed -- it already had exactly one
`kind="state"` accessor).

### Front-matter

`accessors:` list unchanged (`[selected_rows]`).

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example -- reused this guide's existing `maxBytes`/downsampling Gotchas content and its own ITables-vs-render.DataGrid comparison table rather than re-deriving numbers.
