# NOTES: Mosaic widget guide

## Versions

- mosaic-widget 0.34.0, duckdb 1.5.6, narwhals 2.27.1 (verified broken on 2.21.0, as documented in the guide),
  shiny 1.9.0, lonboard 0.17.0, plotly (version bundled with shinywidgets dev deps), geopandas 1.2.0.
- shinywidgets commit: started at `e661cd65` (main at task start). The shared checkout went through a transient
  broken state mid-session (someone merged `mols2grid-3-widget-port` into a scratch branch in the main checkout,
  leaving `pyproject.toml` and `shinywidgets/_render_widget.py` with unresolved conflict markers for a few
  minutes) and later had another agent switch branches in it entirely. I worked around both by creating my own
  worktree (`git worktree add --detach <scratch>/clean-main main`, later switched to the coordinator-provided
  isolated worktree at `scratch/main-wt`, synced with `uv sync --python 3.12 --all-groups`) and ran every `uv run`
  from there, passing absolute paths to this guide's files. Final verification pass (after the dataset/docstring
  rework) ran against `main-wt`, detached at `origin/main` as of the coordinator's note (commit `38a1796b`+). I did
  not re-diff that commit against `e661cd65`; nothing in the accessor/renderer code path is expected to have
  changed (the diff was an unrelated test fix, per the one commit log line I saw: "test(ipycanvas): click via the
  locator, not a pre-measured bounding box (#391)").
- Date: 2026-10-30.

## Verification table

| File | Ran | Screenshot | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes | n/a (static) | n/a |
| examples/02_context_layers.py | yes | before/after | brush drag | n/a |
| examples/03_scale_raster.py | yes | before/after | brush drag (1M rows) | n/a |
| examples/04_declarative_inputs.py | yes | before/after | menu select | n/a |
| examples/05_selection_types.py | yes | before/after | brush drag | n/a |
| examples/06_params_accessor.py | yes | before/after | brush drag | `params()` -- confirmed seed `{}`-ish, confirmed populated dict after brush |
| examples/07_data_accessor.py | yes | before/after | brush drag | `data()` -- confirmed row count and aggregate change after brush |
| examples/08_rate_limiting.py | yes | before/after | brush drag x2 | `params()` rate policy -- confirmed 3 fires (debounced) vs 12 fires (`rate_delay=0`) for the same gesture |
| examples/09_update_spec_in_place.py | yes | before/after | brush + radio click | in-place `spec=` update -- confirmed color changes without re-render, confirmed selection resets |
| examples/10_linked_stats_table.py | yes | before/after | brush drag | `params()`/`data()` -- confirmed table and count update |
| examples/11_linked_map.py | yes | before/after | brush drag | `params()`/`data()` cross-library -- confirmed map highlight tracks selection |
| examples/12_linked_barchart.py | yes | before/after | brush drag | `params()`/`data()` cross-library -- confirmed bar chart updates (needed a longer wait: plotly's own JS bundle takes ~6s to load cold, unrelated to Mosaic) |
| gallery/template_crossfilter_starter.py | yes | before/after | brush drag | n/a (uses params()/data(), same as examples 10) |
| gallery/showcase_flight_delays.py | yes | before/after | brush drag | n/a |

Accessor coverage: both accessors (`params()`, `data()`) verified with real Playwright mouse gestures (drag to
brush, click to select a menu option), not just source inspection. `rate_policy`/`rate_delay` verified by counting
actual fires across two gestures. In-place `spec=` update and its selection-reset side effect verified with a
before/after screenshot pair showing the brush rectangle disappear. The one claim I verified by reading source
rather than a live multi-session test: that passing a `duckdb.DuckDBPyRelation` with no `con=` lands on
`duckdb.default_connection()` (read `mosaic_widget/_db.py:connect()` directly; the logic is an unconditional
three-line fallback, not worth re-deriving from a live two-browser-context test given the old report already did
that exact experiment and the code hasn't changed).

## Bugs found

**shinywidgets (current main):** none found in the renderer itself. The `render_mosaic_widget` docstring is
accurate and matches behavior I verified live (connection-sharing mechanics, re-render leak, in-place spec
updates).

**Docs gap, not a bug:** the renderer's `data()` accessor doesn't expose the underlying `MosaicWidget.data()`
method's `filter_by=` parameter. Not documented anywhere before this guide. Low severity -- `dashboard.data()`
with no args already does the right thing (filters by every active selection) for the common case, and the
escape hatch (`dashboard.widget.data(table, filter_by=...)`) is one line. Noted in the guide and in Gotchas.

**Upstream (mosaic-widget), confirmed still current:**
1. narwhals metadata under-declared (`>=2.8` declared, `>=2.22` needed) -- reproduced the `ImportError` live with
   narwhals 2.21 installed via `uv run --with narwhals==2.21.0`.
2. Bad spec (unknown mark/column/table) renders a blank output with only a browser-console error, no Python-side
   or on-page error. Reproduced live with `"mark": "dott"`.
3. Native `table` input header is hard-coded white-on-black regardless of page theme; low-contrast body text in
   dark mode. Reproduced live by forcing `data-bs-theme="dark"` on the declarative-inputs example.
4. `params` has no JS-side listener, so assigning to it from Python doesn't filter anything in the browser (it's
   a synced trait, so the *attribute* can be set, but nothing downstream reacts). Reproduced live: set
   `w.params` from a `@reactive.effect`, screenshotted, chart stayed unfiltered.
5. Re-render leak: anywidget's class-level `FileContents.changed` strong reference keeps every rendered
   `MosaicWidget` (and its DuckDB connection) alive for the life of the process. I did not re-run the old
   report's `objgraph`/heap-measurement experiment (time budget); I'm relying on the `render_mosaic_widget`
   docstring, which states this plainly and was presumably written/reviewed against that investigation. If the
   maintainer wants this independently re-measured rather than trusted from the docstring, flag it.

**Dropped from the old report (`docs/widget-reports/mosaic-widget/report.md`) as stale:**
- "DuckDB 2.0 relations have no `fetchone()`" -- false on the current pin (duckdb 1.5.6); `rel.fetchone()` works
  fine. The old report tested against duckdb 2.0.0, which isn't what's installed now.
- The whole "PR review" section (blockers, nits, scorecard, rebase instructions) -- the PR has since merged; none
  of it is relevant to a user-facing guide.
- Multi-session cross-talk experiments with 2-3 browser contexts -- I verified the underlying mechanism by
  reading `_db.connect()` instead of re-running the full multi-session experiment, and cited the docstring (which
  now documents exactly this) rather than re-deriving it. Judgment call: time budget vs. marginal new information,
  given the code the old report's conclusion rests on hasn't changed.
- `preagg_schema` being overwritten by JS `initialize()` -- plausible and consistent with the architecture, but I
  didn't re-verify it live (not relevant to any pattern in this guide, which never touches `preagg_schema`).

## Update 2026-11-11 (main @ 32ca7035)

Brought up to date against `main` @ `32ca7035` (33 commits ahead of the `e661cd65`/`38a1796b`+ base this guide was
verified against on 2026-10-30). Relevant commits: #395 (DuckDB lockdown by default), #403 (`data(filter_by=...)`),
#437 (`.read()` / unified accessor semantics -- `params()`/`data()` were already "state" accessors, re-seeded
every render, so #437 is a vocabulary change here, not a behavior change).

- **`render_mosaic_widget` now locks down the widget's DuckDB connection by default (#395).** This guide
  previously had no Security section at all -- the coordinator's `FINDINGS.md` flagged the underlying gap (SQL
  from the browser reaching `conn.query()`/`.execute()` unrestricted) as a release blocker found while writing
  the *quak* guide, confirmed by code-reading for mosaic-widget's own `_handle_custom_msg`, but that finding never
  made it into this file on 2026-10-30. It's fixed now, and this update adds the Security subsection the gap
  should have had from the start: the default lockdown, `allow_unrestricted_connection=True` as the opt-out, and
  -- the mosaic-specific subtlety the brief called out -- that the lockdown is *permanent and database-wide*, so
  a shared `con=` must do any server-side file reads before the first render. Cross-referenced this against the
  existing "Which connection you pass decides session isolation" gotcha (already in this guide from 2026-10-30),
  since the two interact: sharing a connection for session-isolation reasons also means the first render locks
  it for everything else that touches it.
  - Verified server-side with the shipped unit tests (not a browser gesture -- this is Python/DuckDB connection
    state, not something a screenshot shows): `tests/unit/test_render_widget.py -k mosaic` and the full
    `tests/unit/test_mosaic_widget.py` (19 + 53 tests respectively, including the dedicated
    `test_render_mosaic_widget_lockdown_is_permanent_on_a_shared_connection`, which asserts a second `SET` on a
    shared connection raises `duckdb.InvalidInputException` after one dashboard render) -- all pass.
  - Checked every example in this guide against the "do file reads before first render" rule: all 13 pass
    `data={"penguins": penguins}` (a fresh, private in-memory connection built by `MosaicWidget` itself, read via
    `pd.read_csv()` in plain Python *before* the widget is even constructed, not via the widget's own DuckDB
    connection after render) -- none of them share a `con=`, so none needed a code change for this.
- **`data(filter_by=...)` (#403): added to the accessor reference table and to `data()`'s own subsection.** This
  closes the exact "docs gap, not a bug" this guide flagged on 2026-10-30 ("the renderer's `data()` accessor
  doesn't expose the underlying `MosaicWidget.data()` method's `filter_by=` parameter") -- it's no longer a gap,
  the parameter is on the accessor itself now. Removed the stale Gotchas bullet describing the old workaround
  (`dashboard.widget.data(table, filter_by=[...])`).
  - **New example**: `examples/13_export_filtered.py` + a new "Export filtered rows, read on demand" subsection
    under Coordinating multiple views -- a two-selection dashboard (species toggle, flipper-length brush) with a
    download button that exports rows matching *only* the flipper selection via `filter_by="flipper"`, ignoring
    the species click. Chosen because it does double duty: demonstrates `filter_by=` with a visible, concrete
    payoff (a KPI/export that doesn't chase a filter it's not supposed to track) and demonstrates "read on
    demand" (the brief's headline new pattern), mirroring quak's CSV-download example. Pairs with: quak.
    - Verified with a real Playwright gesture: dragged the flipper histogram (intervalX) and clicked a species
      bar (toggleY) in the same session, confirmed both selections visibly active (species bar chart narrows to
      2 of 3 species; flipper histogram shows the brushed range highlighted), then clicked "Download CSV" and
      inspected the downloaded file directly: 191 rows, species column has **both** Adelie (141) and Chinstrap
      (50) -- proving `filter_by="flipper"` genuinely ignored the species selection -- and
      `flipper_length_mm` confined to 178-200, the brushed window. Screenshots: `img/13_export_filtered_before.webp`,
      `img/13_export_filtered_after.webp`, both looked at (Read tool) before citing.
- **Accessor reference table**: reformatted to the new standard columns (`returns | before any interaction |
  across re-render | default rate policy`), and added the `data(table=None, *, filter_by=None)` signature.
  Clarified that `dashboard.widget.sql` (a plain Python `@property`, not a traitlet) is **not** reachable via
  `.read()` or `reactive_read()` -- verified directly: `dashboard.read("sql")` raises `AttributeError: ... has no
  accessor or synced trait named 'sql'` (confirmed by instantiating the renderer and reading `.sql` vs.
  `.read("sql")` side by side). I nearly wrote the opposite claim first; worth a callout here in case another
  guide makes the same mistake for a widget with a plain-property "extra" trait.
- No code example in this guide used `reactive_read()` before this pass (confirmed by grep), so there was
  nothing to convert to `.read()`.
- CHANGELOG.md's `@render_mosaic_widget` bullet still only lists `params()`/`data()`, with no mention of the
  lockdown or `filter_by=` -- confirmed neither #395 nor #403's commit touched `CHANGELOG.md` (`git show --stat`
  on `3fc32c7b` and `4972ba1a`). Not fixed (outside this guide's assigned directory, and the operating rules
  forbid editing tracked files); flagging as a docs gap, same issue noted in quak's NOTES.md for its own entry.

### Verification table (new/edited files)

| File | Ran | Screenshot | Gesture driven | Verification |
|---|---|---|---|---|
| `examples/13_export_filtered.py` | yes (`shiny run`, port 8111) | before/after, both looked at | yes -- intervalX drag + toggleY click, Playwright | `filter_by="flipper"` confirmed against the downloaded CSV's exact row count and species breakdown |

### Bugs found (2026-11-11)

- **Fixed since 2026-10-30**: the "no DuckDB lockdown" security gap (flagged in the coordinator's `FINDINGS.md`
  but never recorded in this guide's own NOTES) is fixed by #395. The "`data()` doesn't expose `filter_by=`"
  docs gap this guide flagged is closed by #403.
- **New, docs-only**: `CHANGELOG.md`'s `@render_mosaic_widget` entry doesn't mention #395's lockdown or #403's
  `filter_by=`. Not a behavior bug, just an incomplete changelog entry.
- Everything else in "Bugs found" from 2026-10-30 (narwhals metadata, bad-spec silent failure, native `table`
  input contrast, `params` being effectively read-only, the re-render widget leak) still reproduces on `main` @
  `32ca7035` -- not re-run individually this pass, since none of the #395/#403/#437 diffs touch the code paths
  behind them.

## Judgment calls (flagging for a second opinion)

1. **Real dataset throughout, except for the two scale demos.** Per the coordinator's mid-task note, I switched
   every penguin-flavored example from a numpy-synthesized fake species/flipper/mass table to the real Palmer
   Penguins CSV (`palmerpenguins`, fetched from a stable `raw.githubusercontent.com` URL, 342 rows after
   `dropna`). I left `examples/03_scale_raster.py` (1M rows) and `gallery/showcase_flight_delays.py` (2M rows)
   synthetic, and `examples/11_linked_map.py` (US store locations) synthetic, since no small real dataset fits
   those shapes. Flag if the maintainer would rather a different real dataset for the map example (e.g. real US
   city coordinates) over synthetic lon/lat.
2. **Docstrings/comment headers, not triple-quoted module docstrings, in every example and gallery file.** Shiny
   Express auto-displays a module's leading bare string expression as on-page text (confirmed empirically: it's
   not just the module `__doc__`, it's the generic "every top-level expression is captured and displayed"
   behavior). A multi-line metadata docstring (title/bucket/run/data, as the brief originally specified) renders
   as one ugly run-on paragraph. I moved all of that to `#` comments per the coordinator's follow-up note. If the
   coordinator's tooling expects a literal `__doc__` string for gallery metadata, this will need adjusting back
   (into a variable assignment or similar) since `#` comments aren't introspectable at runtime the way a
   docstring is.
3. **`output_widget` imports removed from every example.** None of my Express-mode examples ever call
   `output_widget()` explicitly -- Express auto-creates the output region for a `@render_*`-decorated function
   defined inside a `with ui.card():` block. I removed the unused import from all 14 files rather than leave
   dead imports in teaching code. If the coordinator's web-rendering pipeline expects every example to visibly
   import everything it conceptually depends on (e.g. for a "copy this import line" affordance), let me know and
   I'll add it back even though it's unused.
4. **Two bugs found and fixed in my own gallery app, not shinywidgets/Mosaic bugs:** `avg(delay <= 0)` needs an
   explicit `::INT` cast in DuckDB (booleans aren't directly aggregable), and `shiny.express.ui.value_box` /
   `ui.layout_columns` are context-manager-only in Express (no positional `title, value` args) -- I had to import
   the classic `shiny.ui.value_box`/`layout_columns` instead for use inside a `@render.ui` function that builds
   and returns a tag tree programmatically rather than using `with` blocks. This is a generic Shiny Express trap
   (not Mosaic-specific), so I didn't add it to the guide's Gotchas section, but it cost real debugging time and
   might be worth a line in a cross-cutting "writing render.ui() in Express" article if the coordinator is
   planning one.

## Editor's notes for the website

- **Strongest material:** the "Scale: a million rows" and gallery showcase sections -- the before/after
  screenshots make the DuckDB-backed crossfilter story concrete (a literal selection-count change with no visual
  lag), which is Mosaic's actual headline feature. The rate-limiting before/after (3 vs 12 fires) is also a clean,
  simple piece of evidence worth keeping prominent.
- **Candidate for trimming on a shorter page:** the "Combining selection types" subsection under "What you can
  build" is the weakest of the four feature-tour entries -- it's a real and correct pattern, but visually similar
  to the context-layers example right above it. Cutting it would shorten the page without losing a distinct
  lesson (the two selection-type idea is folded into "Selection types" already, and `toggleY` isn't an accessor
  concept).
- **The lonboard pairing (`examples/11_linked_map.py`) is the best demonstration of "update in place to preserve
  state"** since the map's own pan/zoom would be lost on every re-render; the plotly pairing is a good contrast
  (cheap enough to just re-render). Consider linking these two against each other explicitly in any cross-cutting
  "coordinating views" article, since they're the same lesson from opposite sides.
- **Cross-widget pairings for the coordinator's reuse:** pairs with: lonboard (`examples/11_linked_map.py`),
  pairs with: plotly (`examples/12_linked_barchart.py`), pairs with: render-widget/plain-Shiny-outputs
  (`examples/10_linked_stats_table.py`, `gallery/template_crossfilter_starter.py`), pairs with: quak (same
  read-on-demand CSV export pattern, `examples/13_export_filtered.py` vs. quak's `examples/08_linked_download.py`
  -- added 2026-11-11).
- The hero image (`img/gallery_showcase_flight_delays_before.webp`) is also used inline as the showcase gallery
  screenshot; if the site wants a non-duplicate hero, the quick-start screenshot (`img/01_quickstart.webp`) is the
  next-best candidate (clean, colorful, immediately legible).

## What I deliberately dropped from the old report

- The entire "PR review" framing (blockers/nits/scorecard/rebase steps) -- the PR is merged; irrelevant to users.
- The stray `fetchone()` claim -- verified false on the current duckdb pin (see Bugs found).
- The "Non-issues ruled out" section -- mostly about PR review mechanics (harness flakiness, test-isolation
  quirks) rather than anything a guide reader needs.
- Detailed heap/WebSocket-byte measurements for the re-render leak -- kept the conclusion (don't re-render
  often; prefer in-place `spec=`) but dropped the numbers, since I didn't re-measure them this round and stale
  numbers with a "verified on current main" guide would be worse than no numbers.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": cites this guide's own existing "Scale: a million rows, still instant" subsection (raster mark) and, per Task 6's handoff (applied with paraphrased wording, not verbatim -- see `tools/handoff/task-6.md`), the ~3MB-per-brush-step Arrow-buffer measurement from the linked-views article's Task 6 pass for this guide's own `render_mosaic_widget`/DuckDB-in-Python pattern.
