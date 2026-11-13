# NOTES: reactable guide

## Versions

- Date: 2026-10-30
- shinywidgets: `0.8.2.post1.dev103+gf8238de6` (commit `f8238de6`, current `main` as of writing; this
  checkout underwent a live `git merge origin/main` mid-session that touched `shinywidgets/_render_widget.py`
  and `pyproject.toml` -- all findings below were re-verified *after* that merge completed)
- reactable: 0.1.6
- ipyreact: 0.4.1 (resolved by `uv run --no-sync --with reactable ...`; the repo's `tool.uv.override-dependencies`
  targets the shared lock, which an ephemeral `--with` overlay doesn't use -- not re-tested against 0.7.0, but
  the old spike report says both versions behave the same here)
- shiny: 1.9.0
- pandas: 3.1.0
- Python: 3.12 (the `--with reactable` overlay's resolved interpreter)

## Verification table

| File | Ran | Screenshot | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes | n/a | n/a |
| examples/02_formatting_styling.py | yes | yes | n/a | n/a |
| examples/03_grouping.py | yes | yes | yes (expand group) | n/a |
| examples/04_expandable_details.py | yes | yes | yes (expand rows) | n/a |
| examples/05_custom_cells.py | yes | yes | n/a | n/a |
| examples/06_theming.py | yes | yes | n/a | n/a |
| examples/07_column_groups_footers.py | yes | yes | n/a | n/a |
| examples/08_selected_rows.py | yes | yes (before/after) | yes (check boxes) | `selected_rows()` yes |
| examples/09_page_sorted.py | yes | yes | yes (sort + next page) | `page()`, `sorted()` yes |
| examples/10_filter_search.py | yes | yes | yes (type into filter + search) | `filtered()`, `search()` yes |
| examples/11_rate_limiting.py | yes | yes | yes (typed, timed at 400ms/1100ms) | `search()` debounce override yes |
| examples/12_inplace_props.py | yes | yes (before/after) | yes (dragged slider) | n/a (non-accessor in-place update) |
| examples/13_update_data.py | yes | yes (before/after) | yes (sort, then click buttons) | n/a (in-place data update + re-render) |
| examples/14_selection_to_detail.py | yes | yes (before/after) | yes (row click via `on_click="select"`) | `selected_rows()` yes |
| examples/15_search_to_chart.py | yes | yes (before/after) | yes (typed search) | `search()` yes |
| examples/16_row_click.py | yes | yes | yes (clicked a cell) | n/a (plain Shiny input, not an accessor) |
| gallery/template_filterable_table.py | yes | yes (before/after) | yes (checked boxes) | `selected_rows()` yes |
| gallery/showcase_cars_dashboard.py | yes | yes (flat/selected/grouped) | yes (row click, search, group toggle) | `selected_rows()`, `search()` yes |

All five accessors (`selected_rows`, `page`, `sorted`, `filtered`, `search`) were driven with a real Playwright
gesture against the actual table (checkbox clicks, header clicks, pagination buttons, typed filter/search text)
and confirmed by rendering the value to a `@render.code` output and reading it back. `page()`/`sorted()` were
exercised together in example 09; `filtered()`/`search()` together in example 10; both pairs also individually
exercised inside examples 14/15/gallery.

**Workaround used only for verification, not shipped in any example file**: every accessor currently throws
`KeyError` on `main` (see Bug 1 below). To verify behavior and take real screenshots, I ran example/gallery files
through a small scratch launcher
(`.../scratchpad/agents/reactable/probe/run_patched.py`) that sets
`shinywidgets._render_widget.render_reactable._accessor_specs = shinywidgets._reactable.REACTABLE_ACCESSORS` at
import time (an in-process monkeypatch, no tracked file edited) before serving the app with uvicorn. Every
screenshot and behavior described in `guide.md` reflects reactable's actual, intended behavior once that one-line
typo is fixed -- none of it is speculative.

## Bugs found

### 1. All five `render_reactable` accessors are broken on current `main` (shinywidgets, regression, high severity)

`shinywidgets/_render_widget.py` line ~5312, in `class render_reactable`:

```python
accessor_specs = REACTABLE_ACCESSORS
```

Every other renderer in the file sets `_accessor_specs` (leading underscore); `render_widget_base.__init__` reads
`type(self)._accessor_specs` to build the `Accessors` runtime. Because `render_reactable` sets the public name
instead, `type(self)._accessor_specs` resolves to the base class's empty default `()`, so
`Accessors(specs=())` is built with no slots at all. Calling **any** accessor --
`tbl.selected_rows()`, `.page()`, `.sorted()`, `.filtered()`, `.search()` -- raises:

```
KeyError: 'selected_rows'
  File ".../shinywidgets/_accessors.py", line 227, in read
    slot = self._slots[name]
```

Minimal repro: `uv run --no-sync --with reactable pytest tests/playwright/render_reactable -q` --
`test_reactable_state_accessors`, `test_reactable_selected_rows_accessor`, and
`test_reactable_accessors_survive_rerender` all fail with this `KeyError` (5 of the file's 8 tests still pass;
those 3 are exactly the accessor-reading ones). This is a **pure typo regression**, not a design or upstream
issue -- the bridge itself (`shinywidgets/_reactable.py`, `js/src/reactable.ts`) is correct and fully functional,
as confirmed by patching the one attribute name at runtime (see above) and re-running the same Playwright suite
green, and by all the gesture-driven verification in this guide.

Likely uncaught because: (a) reactable is excluded from the shared dev/test groups and CI (per `pyproject.toml`'s
own comment), so this never ran in CI; and (b) the one unit test that checks the attribute,
`test_renderer_declares_the_accessors` in `tests/unit/test_reactable_accessors.py`, asserts
`r.accessor_specs == sr.REACTABLE_ACCESSORS` -- i.e. it accesses the same (wrong) public attribute the renderer
sets, so it passes regardless of the typo. A one-character fix (`accessor_specs` -> `_accessor_specs`) resolves
it; I did not make this change per instructions to report, not fix, bugs found in shinywidgets.

### 2. `render_reactable` docstring is wrong about in-place data updates (shinywidgets, docs bug)

The docstring says: "reactable's JavaScript reads the data once when the widget is created, so mutating
`.widget.props["data"]` in place has no effect." This matches the old spike report's finding (`docs/widget-reports/reactable/report.md`,
finding 3) but is **not true on current `main`**. Verified: `tbl.widget.props = {**tbl.widget.props, "data":
new_data}` (a full trait reassignment, not an in-place dict mutation without reassigning -- that part of the
docstring's framing is trivially true of any traitlets trait and not reactable-specific) immediately refreshes
the displayed data, **and preserves the table's current sort/filter/page/selection** (`examples/13_update_data.py`,
screenshots `13_update_data_before.webp`/`_after.webp`: sorted ascending by price, update in place, same row order,
new prices).

Root cause: reactable-py's JS bundle exports two components. `ReactableData` (unused by reactable-py's Python
side) does memoize data with `useMemo(() => normalizeColumnData(data, columns), [])` -- that's what the old
report and the current docstring describe. But the component reactable-py actually mounts by default,
`Reactable2`/`Reactable` (the bundle's default export), recomputes `data = normalizeColumnData(data, columns)`
on every render with no memoization at all. I don't know whether this changed between reactable-py releases or
whether the old report's agent investigated the wrong component; either way, the shipped behavior as of
reactable-py 0.1.6 contradicts the docstring. I did not edit the docstring (reporting, not fixing), but flagged
the correction prominently in `guide.md`'s "Updating the widget from Python" section.

A secondary, newly-discovered detail: the `dataKey` prop (mentioned in passing in the old report as "the bundle
only mentions dataKey in comments") is used as `key={dataKey}` on the actually-mounted `Table` component --
changing it forces a full remount, which is the way to reset sort/filter/selection/expanded state to defaults
after a data swap while still avoiding re-creating the whole Shiny widget/comm. Not covered in the guide body (to
avoid scope creep) but worth a maintainer follow-up; see Judgment calls below.

### 3. `aggregate="mean"`/`"sum"`/`"median"` silently produce blank cells with pandas data (upstream bug, reactable-py)

Verified via direct inspection of `reactable/static/reactable-py.esm.js` plus browser confirmation. `reactable-py`'s
`_tbl_data.py` has a `col_type()` singledispatch with a correct numeric-detection branch for polars `Series`
(`dtype.is_numeric() -> "numeric"`) but the pandas `Series` branch is a stub: `return "UNKNOWN"` unconditionally,
regardless of dtype. The JS side's `getAggregateFunction(name, type)` only looks up `mean`/`sum`/`median` in a
`numericAggregators` dict gated on `type === "numeric"`; everything else (`count`, `max`, `min`, `unique`,
`frequency`) is in a type-agnostic `defaultAggregators` dict and works regardless. Net effect: with a pandas
DataFrame (reactable-py's most common input), `aggregate="mean"` compiles to no aggregate function at all and
the grouped cell renders empty -- no console error, no exception, just blank. Confirmed working via the
type-agnostic aggregators, via a `JS()`-based aggregate function (bypasses the string lookup entirely -- this is
the workaround shown in the guide), and via an equivalent polars DataFrame (where `col_type` correctly reports
`"numeric"` and `aggregate="mean"` works as documented). This is an upstream reactable-py bug, unrelated to
shinywidgets; not something shinywidgets can paper over without its own aggregate-translation layer, which felt
out of scope for a renderer whose job is coercion and layout, not re-implementing the library's column-typing.

### 4. A details column needs its own `html=True` (docs/API-surface nuance, not strictly a bug)

`Reactable(df, details=some_fn)` (passing a bare function as the table-level `details=` InitVar) renders the
returned HTML string as escaped literal text, not markup -- `<div>...</div>` shows up verbatim in the expanded
row. The fix is to wrap it: `details=Column(details=some_fn, html=True)`. This matches reactable-py's documented
column model (every `html` toggle lives on `Column`), so I'm not calling it a bug, but it's an easy trap (the
table-level `details=` InitVar's own type hint, `JS | Column | None`, doesn't make the `Column(..., html=True)`
requirement obvious) and is called out in Gotchas.

### 5. A module docstring renders as visible page content in Shiny Express (general Express behavior, not reactable-specific)

`run_express()` (`shiny/express/_run.py`) executes each top-level statement with `ast.Interactive` and an
overridden `sys.displayhook`, so any top-level bare expression -- including a plain string literal, i.e. a module
docstring -- gets treated as something to display. The brief's gallery-file convention called for a docstring
header; I used a `#` comment block instead once I hit this (confirmed independently before the coordinator's
broadcast note arrived with the same fix). Flagged in Gotchas since it'll bite anyone adapting these examples by
adding a top-of-file docstring.

## Judgment calls

- **Verified against intended behavior, not current `main`'s actual output, for anything accessor-related.**
  Given bug 1 above, every accessor is dead on `main` as checked out. I judged that silently shipping a guide
  full of `KeyError`s (or omitting the headline feature of this release) would be worse than verifying against
  the fix with a one-line in-process patch that touches no tracked file, clearly disclosed here and in `guide.md`'s
  own framing is exactly the intended design per `_reactable.py`'s docstrings, `tests/unit/test_reactable_accessors.py`,
  and `docs/plans/2026-10-30-reactable-accessors.md`. Flag if you'd rather I'd blocked and reported instead.
- **Didn't document the `dataKey` remount technique in the guide body.** It's a real, verified capability (forces
  a clean reset of sort/filter/selection after an in-place data swap, without a full Shiny re-render), but adding
  it would have meant either a third update-pattern example or a denser callout in an already load-bearing
  section. Left as a one-line pointer in Bug 2 above for a maintainer follow-up; happy to add an example if
  wanted.
- **Grouping + selection together**: I did not combine `group_by` and `selection=` in the same table anywhere
  (the showcase toggles between them instead of combining). I checked that reactable-py accepts both props
  simultaneously but didn't verify the resulting `selected_rows()` index semantics against grouped/expanded rows
  (data-space positions get murkier once rows are grouped) -- flagging as untested rather than guessing.
- **SimpleFrame get one line in Gotchas, not an example.** `reactable.data`'s own `SimpleFrame` (the type
  `cars_93` actually is before `.to_pandas()`) has the boolean-indexing quirk from the old report. Every example
  in this guide converts to pandas immediately, per the coordinator's "prefer real recognizable datasets" note
  and to avoid every snippet needing a caveat about it.
- **`07_column_groups_footers.py`'s footer uses `info.values`, not a module-level precomputed mean**, specifically
  so the footer reflects `ColInfo`'s real contract (and doesn't go stale if the data changes) -- a small
  deviation from how I'd first drafted it, worth a glance if reviewing closely.

## Editor's notes for the website

- **Strongest material**: the grouping/aggregation screenshot (03), the custom JS bar-chart cells (05, also used
  as the hero), and the "Updating the widget from Python" before/after pair (13) -- that last one visually proves
  a genuinely surprising, correctly-verified capability (in-place update preserves sort) that contradicts the
  current docstring, and is probably the single most link-worthy thing in this guide.
- **Candidates to cut for a shorter page**: the "Column groups and footers" highlight (07) is the least essential
  of the six "what you can build" items -- cuttable without losing any accessor or layout coverage. The
  "Beyond the accessors: reactive_read" subsection is intentionally one paragraph (there's genuinely nothing to
  add); fine to fold into the accessor reference table's intro if the maintainer wants fewer headings.
- **Accessor coverage is complete** -- all 5 shipped accessors, each with a real gesture and a screenshot. Nothing
  partial here except that it required the in-process patch described above (bug 1 is the blocker, not a gap in
  the guide).
- **pairs with: matplotlib** -- `examples/15_search_to_chart.py` and `gallery/showcase_cars_dashboard.py` both
  drive a `matplotlib`/`@render.plot` bar chart from `search()`; simple, reusable pattern for any "linked views"
  cross-cutting article.
- **pairs with: itables, ipydatagrid, perspective** -- cross-linked in "Learn more" and the intro's
  "choose this vs. siblings" paragraph; no shared example code, just prose pointers.

## Dropped from the old report

- **The CSS-loading and NaN-sanitization findings** (old report findings 1 and 2) are already fixed on `main`
  (shipped renderer behavior, confirmed passing in `tests/playwright/render_reactable::test_reactable_renders_styled`)
  and are mentioned only briefly in the guide's intro, not as a Gotcha -- they're resolved, not a live limitation.
- **"No browser->Python state" (old finding 4) is obsolete**: that was the whole premise the accessor bridge in
  this release fixes. Replaced entirely by the Accessor reference section.
- **The upstream-risk discussion of reactable-py's maintenance status** (from
  `docs/plans/2026-10-30-reactable-accessors.md`'s investigation) isn't reader-facing content; omitted from
  `guide.md`, left in the plan doc where the maintainer already has it.
- **`height=` overridden-in-fill-layout finding (old finding 5)** is already fixed (the renderer now treats a
  user-set `height=` as explicit) and is stated as shipped behavior in "Layout and sizing", not a Gotcha.

## Update 2026-11-11 (main @ 32ca7035)

### What changed and why

- **Bug 1 (all accessors dead via `accessor_specs`/`_accessor_specs` typo) is fixed on `main` by #394**, and
  reactable's unit/Playwright tests now run in CI (#399). The guide's accessor content was already written
  against reactable's intended behavior (verified at the time via an in-process patch, disclosed in this file's
  original "Bugs found" and "Judgment calls" sections); this pass re-verified every accessor with real Playwright
  gestures against **unpatched, current `main`**, with no monkeypatch anywhere in the verification path. No
  wording in `guide.md` ever described the breakage or the patch (confirmed by a full-text search), so there was
  nothing to delete from the guide itself. This NOTES.md keeps the bug-1 history (now marked fixed, below) rather
  than scrubbing it, per the update brief's instruction to record fixed bugs with their PR number.
- **`examples/13_update_data.py`'s in-place comment was stale** -- it said "despite the docstring's warning that
  reactable reads data once," but `render_reactable`'s docstring on current `main` already documents the
  `.widget.props` reassignment pattern correctly (fixed by #398, before this pass started). Reworded the comment
  to state the behavior directly instead of referencing a now-nonexistent docstring warning.
- **`guide.md`'s "Updating the widget from Python" section reframed**: the old text was phrased as "Correction to
  the `render_reactable` docstring" (appropriate when the docstring was wrong); since the docstring is already
  correct on current `main`, reframed it as a plain teaching passage for the reassignment pattern, no mention of
  a prior docstring error.
- **New example, `examples/17_export_selected.py`** ("Read on demand: export selected rows"): a
  `@render.download_button` handler reads `tbl.selected_rows()` cold, at click time, with no other reader of that
  accessor anywhere in the app -- demonstrating the redesign's headline capability (no warm-up idiom needed) with
  a genuinely new pattern the old event/state split couldn't support safely. Added as a new subsection in
  "Reacting to user interaction", between "What's visible" and "Row clicks".

### Re-verification (unpatched main @ 32ca7035)

| Accessor | Gesture | Confirmed | Screenshot replaced |
|---|---|---|---|
| `selected_rows()` | checked rows 0 and 2 in `examples/08_selected_rows.py` | `[0, 2]` | yes (`08_selected_rows_before/after.webp`) |
| `page()` | clicked "price" header then "Next" in `examples/09_page_sorted.py` | `page 2` | yes (`09_page_sorted.webp`) |
| `sorted()` | same gesture | `[{'id': 'price', 'desc': False}]` | yes (`09_page_sorted.webp`) |
| `filtered()` | typed "acur" into the manufacturer filter box in `examples/10_filter_search.py` | `[{'id': 'manufacturer', 'value': 'acur'}]` | yes (`10_filter_search.webp`) |
| `search()` | typed "midsize" into the search box, same app | `'midsize'` | yes (`10_filter_search.webp`) |

Also re-verified `examples/13_update_data.py` (sorted by price, then "Update in place" clicked): row order
(manufacturer/model) identical before and after, only prices changed -- confirms #398's in-place-update-preserves-
sort claim on unpatched main, not just the previously-patched run. Screenshots replaced
(`13_update_data_before/after.webp`).

`examples/17_export_selected.py` verified: checked 2 rows (Acura Legend, BMW 535i), clicked download, read the
downloaded CSV's bytes directly -- contained exactly those 2 rows. Screenshots added
(`17_export_selected_before/after.webp`).

Did not re-run examples 01-07, 11, 12, 14-16, or the gallery apps in this pass (their content didn't change and
nothing in the redesign altered their behavior); their existing screenshots and verification status from
2026-10-30 stand. `11_rate_limiting.py` (debounce override) and `12_inplace_props.py` (non-data prop update) don't
touch any of the five state accessors' *existence*, only their rate policy and an unrelated prop, so re-verifying
bug 1's fix didn't require re-running them.

### Old "Bugs found" status

- **Bug 1 (all accessors raise `KeyError`)**: **fixed by #394** (`_accessor_specs` typo corrected). Reactable's
  tests now run in CI (#399), preventing a recurrence. Re-verified fixed on `main` @ 32ca7035 with real browser
  gestures, no patch.
- **Bug 2 (docstring wrong about in-place `props["data"]` updates)**: **fixed by #398**. The docstring on current
  `main` already states the reassignment pattern correctly; `guide.md` and `13_update_data.py` updated to stop
  referencing the old, now-nonexistent docstring text (see above).
- **Bugs 3-5** (pandas `aggregate="mean"`/`"sum"`/`"median"` blank cells; details column needs its own
  `html=True`; Express module docstrings render as page text): unrelated to the accessor redesign, not retested
  in this pass, still believed accurate (upstream/Express behavior, not touched by any of the 33 commits in this
  update).

### New bugs found this pass

None.

### Front-matter

`accessors:` list unchanged (`[selected_rows, page, sorted, filtered, search]`) -- the redesign didn't add or
rename any reactable accessor.

### Accessor reference table format

The 2026-10-30 version of `guide.md` used the pre-redesign table columns (`Returns | Fires when | None/empty
means | Rate policy`). Replaced with the update brief's required columns (`Returns | Before any interaction |
Across re-render | Default rate policy`), matching the format already in use in `plotly/guide.md`,
`bokeh/guide.md`, and `panel/guide.md`. All five reactable accessors re-seed from the new table on every
re-render (confirmed from `shinywidgets/_reactable.py`'s `state_attach`: the JS bridge reports the *new* table's
full current state on bind, every render, not the old table's last-known value), so the "Across re-render" column
reads "re-seeded" for all five, not "kept".

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example. reactable has no documented downsampling or virtualization (confirmed by reading the whole guide -- it's client-side like itables, but without itables' maxBytes); said so plainly rather than inventing a ceiling, and pointed to ipydatagrid/quak/mosaic for real scale.
