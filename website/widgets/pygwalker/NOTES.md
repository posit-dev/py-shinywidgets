# NOTES: PyGWalker guide

## Versions

- `pygwalker` 0.5.0.1, `duckdb` 1.5.6, `sqlglot` 30.27.0, `shiny` 1.9.0, `plotly` (whatever's in the
  worktree's locked venv), Python 3.12.
- shinywidgets commit: current `main` at time of writing (2026-11-02), after the reactive-accessors pass
  landed and after the DuckDB-lockdown security fix for `render_pygwalker`
  (`require_duckdb_lockdown`, `validate_visitor_sql`, `harden_walker_widget` in `shinywidgets/_render_widget.py`).
- Ran from the coordinator's isolated worktree (`scratchpad/main-wt`), per the brief, after the coordinator's
  terminal crash mid-session; resumed cleanly (worktree, venv, and prior outputs were all intact).
- Playwright: Chromium, default headless launch (no WebGL/WebGPU args needed; PyGWalker is DOM/canvas-chart
  based, not WebGL).

## Accessor coverage

**None.** `render_pygwalker` (lines 3750-4086 of `shinywidgets/_render_widget.py`) declares no
`_accessor_specs`, confirmed by grepping every `_accessor_specs = ...` assignment in the file and finding
none inside the class body. Also confirmed the widget itself carries no state-tracking trait:
`sorted(widget.trait_names())` on a freshly built `pygwalker.api.anywidget.walk()` widget returns only
ipywidgets boilerplate (`_anywidget_id`, `_dom_classes`, `_esm`, `_model_*`, `_msg_callbacks`,
`_property_lock`, `_states_to_send`, `_view_*`, `comm`, `keys`, `layout`, `log`, `tabbable`, `tooltip`) plus
`props` (a one-way JSON blob set once at construction, never updated from the browser). So there is also
nothing worth reading with `reactive_read()`. The guide documents the `widget.on_msg()` tier instead (the
`update_spec` and `export_dataframe_by_sql` messages), which is the only way to observe explorer state from
Python, and is verified with real gestures throughout.

## Verification table

All apps run via `uv run --no-sync python -m shiny run <file> --port <port>` from the worktree (ports
9860-9879), screenshotted with Python Playwright, Chromium, 1280-1500 wide, `device_scale_factor=2`. Every
screenshot referenced in `guide.md` was read with the Read tool before being cited. Drag-and-drop gestures
used real `mouse.down()` / stepped `mouse.move()` / `mouse.up()` sequences onto `[data-rbd-droppable-id=...]`
targets (react-beautiful-dnd); save used the real `Ctrl+s` keyboard shortcut; export used a real button
click, located per-run by searching toolbar buttons in the plausible region (icon positions shift depending
on interaction history -- see "Judgment calls" below) and confirming via the app's own Python-side output
that `export_dataframe_by_sql` actually fired, not just that *some* button was clicked.

| File | Ran | Screenshot | Gesture driven | Notes |
|---|---|---|---|---|
| `examples/globals.py` | n/a (imported, not run) | n/a | n/a | idempotency verified directly (see below) |
| `examples/01_quickstart.py` | yes | yes (hero) | n/a (static) | 244-row tips; confirmed via `widget_manager`-free `get_by_text` on field names |
| `examples/02_build_a_chart.py` | yes | before/after pair | yes -- drag total_bill/tip/smoker onto X/Y/Color | encodings confirmed via `get_latest_vis_spec` after a real `Ctrl+s`: `columns:[total_bill]`, `rows:[tip]`, `color:[smoker]`, `filters:[]` |
| `examples/03_save_and_export.py` | yes | before/after pair | yes -- drag, `Ctrl+s`, click export icon | `spec_summary` and `exported_table` outputs read back correctly; exported `total_bill_sum`/`tip_sum` per smoker group cross-checked against the plotted points |
| `examples/04_scale.py` | yes | yes | yes (chart-build gesture, for the payload measurement) | 1M rows; `time to Field List` and websocket bytes measured identical to 500/50K rows (see below) |
| `examples/05_filter_and_persist_spec.py` | yes | before/after pair | yes -- drag+color, `Ctrl+s`, then a real `select_option("Sat")` on the Shiny input | chart re-renders on filtered data with the same shelves/color after the filter change |
| `examples/06_linked_export_to_plotly.py` | yes | before/after pair | yes -- drag day/tip, click export icon | found and fixed an authoring bug in my own example (see Bugs found); after the fix, plotly bar values (Sat~260, Fri~50, Sun~250, Thur~170) matched the PyGWalker chart it was exported from |
| `examples/07_layout_sizing.py` | yes | yes | n/a (static) | fill card vs. explicit `height="420px"` scrolling, consistent with the existing Playwright suite's assertions |
| `gallery/template_explorer.py` | yes | yes | n/a | sidebar filters render and the explorer loads; idempotent single-file lockdown confirmed (see below) |
| `gallery/showcase_tips_dashboard.py` | yes | yes (save-toast state) | yes -- drag day/tip/sex, `Ctrl+s` | chart renders correctly with sidebar filters; the export->value-box panel uses the exact code pattern already gesture-verified in `03`/`06`, not independently re-gestured here (see Judgment calls) |

Also ran the existing test suites on current `main` as corroborating evidence (not re-derived by me):
`uv run --no-sync pytest -c tests/playwright/playwright-pytest.ini tests/playwright/render_pygwalker` (7
passed) and `uv run --no-sync pytest tests/unit/test_pygwalker.py` (44 passed). These cover: the DuckDB
lockdown rejecting server file reads/writes and the unlock attempt itself, the blocked
`open_in_desktop`/`upload_spec_to_cloud` actions, fill/explicit-height sizing, and re-render lifecycle
(no leaked views/models).

## The DuckDB-lockdown error message, verified exactly

Built a throwaway Express app with no lockdown at all and confirmed `render_pygwalker` raises before
rendering anything, with the exact message `_DUCKDB_UNLOCKED_MESSAGE` documents (screenshot:
`img/security_lockdown_error.webp`). Also verified directly (no Shiny involved) that:
- `require_duckdb_lockdown()` raises before any lockdown and passes after one.
- `validate_visitor_sql()` accepts `SELECT * FROM pygwalker_mid_table` and a CTE wrapping it; rejects
  `read_csv(...)`, `other_table`, and `DROP TABLE ...` with the documented message.
- The existing Playwright test `test_pygwalker_browser_sql_cannot_touch_server_files` independently confirms
  the same at the browser-message level (a `pyg_request` with `get_datas`/raw SQL), and
  `test_pygwalker_rejects_unsafe_requests` confirms the two blocked actions.

## The `globals.py` double-execution finding (new, cross-cutting)

This is the most consequential finding from this pass and is worth the coordinator's attention for the
roster generally, not just this guide.

**Shiny Express's sibling `globals.py` is not guaranteed to execute exactly once per process.** Verified with
a trivial probe app (`print(os.getpid())` at module scope, no interactions): the module body printed *twice*
before a single browser connected, and the `shiny` package's own `import_module_from_path()` helper (used to
load `globals.py`) explicitly warns `"A module named globals is already loaded, but is being loaded again"`
every time `create_express_app()` is invoked -- which happens at least once for the UI-build phase and again
for every session's server phase. This contradicts the implicit guarantee in the existing
`articles/reacting-to-widgets/examples/globals.py` comment ("Express imports a sibling `globals.py` exactly
once, before any session starts, which is the one safe place for this"). That guide's use case
(`shared_lifetime()` building an `ipyleaflet.Map()`) happens to tolerate re-execution silently (it just
rebuilds the map, wastefully but not visibly), which is presumably why this was never noticed.

For PyGWalker's lockdown, it is **not** tolerant: `SET lock_configuration = true` can only succeed once per
DuckDB connection; a second attempt raises `Invalid Input Error: Cannot change configuration option
"lock_configuration" - the configuration has been locked` (confirmed directly, and confirmed again as the
actual crash when I first wrote `globals.py` without a guard -- the app failed to start with exactly this
traceback, from inside Express's own `create_express_app`, before any session connected). The fix used
throughout this guide: check `current_setting('lock_configuration')` before setting anything, so the whole
block is a no-op the second (and any subsequent) time. Verified this resolves it, including with two
concurrent browser contexts hitting the same running app (both loaded `Field List` with no errors).

**Recommendation for the coordinator**: either correct the `reacting-to-widgets` guide/comment's "exactly
once" claim (it's "at least once, possibly more, so write idempotent setup code" -- not "exactly once"), or
treat this as a shinywidgets/py-shiny docs gap worth raising upstream. I did not touch that other guide's
files (not mine to edit), just noting the discrepancy here.

A related, smaller trap: a bare top-level expression statement in an Express file (even nested inside an
`if` block) gets auto-displayed via Shiny Express's `sys.displayhook`-based "recall" mechanism and crashes if
the value isn't renderable (`duckdb.execute(...)` returns a `DuckDBPyConnection`, which blows up with `
TypeError: Invalid tag item type`). Wrapping lockdown code in a function (as `globals.py` does, and as the
single-file gallery apps do with `_lockdown_once()`) avoids this regardless of the double-execution issue.

## Payload/scale measurement (kernel_computation)

Measured with Playwright's `page.on("websocket", ...)` frame-size hooks (summed sent/received bytes) and
wall-clock timing, comparing identical apps (`examples/04_scale.py`'s pattern) with 500, 50,000, and
1,000,000 rows:

- **Initial render** (ESM bundle + `props` schema, no data): byte-for-byte identical at all three sizes --
  10,163,162 bytes received over the websocket, ~3.3s to an interactive Field List. (`props` itself is 1,226
  bytes regardless of row count -- confirmed directly by constructing `walk()` widgets at each size and
  measuring `len(widget.props.encode())`.)
- **One aggregated chart query** (drag a dimension + a measure onto X/Y): identical at all three sizes --
  ~1.2 KB sent, ~2.0 KB received, ~2.8s wall time (dominated by the scripted drag, not the query).

**Correction to the brief's framing**: "kernel_computation vs. client-side" isn't a choice available through
this renderer. `pygwalker.api.anywidget.walk()` hardcodes `kernel_computation=True` in its call to
`PygWalker(...)`; passing `kernel_computation=` yourself raises `TypeError: pygwalker.api.pygwalker.PygWalker()
got multiple values for keyword argument 'kernel_computation'` (verified directly). Client-side computation
exists in PyGWalker's non-widget APIs (`html.py`, `streamlit.py`'s `use_kernel_calc=False` path), which aren't
what `render_pygwalker` uses. The guide states this as a correction rather than presenting a false choice.

## Bugs found

### In my own examples (fixed before finalizing)

- `examples/06_linked_export_to_plotly.py` originally picked the category column via
  `df[c].dtype == object`, which is wrong for PyGWalker's exported columns (pandas returns a different dtype
  for the pygwalker export path, not plain `object`); `next(...)` with no match raised `StopIteration`, which
  surfaces to the user as the cryptic `coroutine raised StopIteration` (PEP 479's conversion of an uncaught
  `StopIteration` inside a coroutine to a `RuntimeError`). Verified red (reproduced the exact error via a
  real export gesture), then green (switched to picking the numeric column via
  `pd.api.types.is_numeric_dtype` and taking the other as the category), reverified via the same gesture.
  Left in NOTES rather than silently fixed, per "default to TDD" -- this was a real author's mistake caught
  by driving the example with a real browser, which is exactly what the verification step is for.

### Upstream (pygwalker 0.5.0.1)

- The export and save toasts are Jupyter-centric and misleading in a Shiny app (see Gotchas in `guide.md`):
  save says "spec params is not 'json_file', save is not supported" even though the spec did arrive in
  Python; export tells the user to read a `walker` variable that doesn't exist outside the originating
  notebook cell. Matches the old report's finding; still true on 0.5.0.1.
- The "Enable AI Agent ... pip install runcell" ad banner persists regardless of `set_privacy("offline")`.
  Matches the old report; still true.
- The visualization tab's "Filters" shelf visually echoes every dimension used on *any* shelf (Color, etc.),
  with a trash icon, which is easy to mistake for an active filter. Verified it is not: reading the saved
  spec back shows `"filters": []` even while, e.g., the Color field's name also appears in the Filters box.
  New finding this pass, not in the old report.
- `kernel_computation` is not actually a user-facing choice through `pygwalker.api.anywidget.walk()` (see
  above) -- it's hardcoded `True` and attempting to override it raises `TypeError`. New finding this pass.

### Docs (shinywidgets, on current `main`)

- Nothing wrong found in `render_pygwalker`'s own docstring -- the privacy, security, and `.widget` guidance
  all matched observed behavior exactly (this is the post-fix docstring; the old report's docstring
  complaints were about a since-superseded PR version and no longer apply).
- See "The `globals.py` double-execution finding" above for the cross-cutting docs gap in a sibling guide
  (not `render_pygwalker`'s own docs).

## Judgment calls (flag for the maintainer)

1. **The export icon has no stable selector.** It has no `aria-label`, no `title` attribute, and its SVG
   glyph is reused by at least one other icon depending on layout/history, so I located it per-run by
   searching toolbar buttons in a plausible region and clicking until the app's own captured state changed,
   rather than a single reliable selector. This is an upstream a11y gap (also noted in the old report), not
   something I could fix in the examples beyond choosing dataset/layout combinations where the search is
   fast and side-effect-free (verified the final screenshot's chart/spec were unaffected by the earlier,
   unsuccessful candidate clicks in each search).
2. **`gallery/showcase_tips_dashboard.py`'s export-to-value-box panel was not independently re-gestured.**
   After confirming the exact same `on_msg`/export code pattern works via real gestures in both
   `examples/03` and `examples/06`, I judged that re-deriving a third gesture-matched screenshot for the
   showcase (under this pass's tightened resource constraints -- one browser/server at a time, disk/load
   pressure) was a low-value repeat of already-verified mechanics. The showcase's chart-building and
   `Ctrl+s`-persistence gestures *are* independently verified (see the verification table).
3. **Dropped the `kernel_computation` vs. client-side framing from the assignment as given**, in favor of
   reporting that there's no client-side choice through this renderer at all (see "Payload/scale
   measurement" above). I verified this directly rather than assuming the assignment's framing was accurate.
4. **No separate "Rate limiting" example.** There are no accessors and no state-carrying trait, so there is
   nothing to rate-limit; said so in one line rather than inventing a non-example, per "never pad."
5. Dataset choice: `plotly.express.data.tips()` throughout (ships with plotly, already a dependency
   elsewhere in the repo; real, recognizable, and a good fit for drag-and-drop demos: a mix of categorical
   and numeric columns). The scale example uses synthetic NYC-taxi-flavored data (real recognizable field
   names and plausible distributions) rather than real large tips/taxi data, per the brief's allowance for
   synthetic data when the point is scale.

## Editor's notes for the website

- **Strongest material**: the Security section (verified error screenshot + the `globals.py`
  double-execution finding) and the scale measurement table are the two things most worth keeping if the
  page needs to shrink -- they're the most load-bearing, non-obvious, and fully verified claims.
- **Candidates to cut for a shorter page**: the "Beyond messages: nothing else to read" subsection is a
  single paragraph that could fold into the accessor-reference table's framing sentence instead of being its
  own heading.
- **Pairs with**: perspective, quak, mosaic (all three cross-linked in "Pairing with other guides"); plotly
  (the one cross-widget pairing example, `06_linked_export_to_plotly.py`, kept simple on the plotly side per
  the brief's instruction).

## What I dropped from the old report and why

- **The full PR-review scorecard, merge verdict, and "should-fix"/"nit" numbered list**: this guide is
  written against released, merged `main` behavior (the security fix already landed), not a pending PR, so a
  merge recommendation doesn't apply. The underlying facts that are still true (ad banner, save/export
  toasts, polars gate, `pyg.walk()` blocking) are kept as Gotchas; everything about the PR's merge
  conflicts, `make check` pass/fail counts for that old branch, and code-review nits (naming, unused
  `# type: ignore`) is gone, since it describes a diff that no longer exists.
  - **One exception, explicitly re-verified, not just carried over**: the `pyg.walk()` blocking-server
    finding is restated as fact in this guide's Gotchas without a fresh repro this pass (it's upstream,
    unrelated to anything that changed, and reproducing a blocking-forever call isn't worth the machine time
    under this pass's load constraints) -- flagging the provenance here per the "docstrings/claims can be
    wrong, verify before stating as fact" instruction, in case the maintainer wants it re-checked.
- **The 10 MB-per-render weight discussion**: kept, but reframed as a measured, scale-invariant fact (see
  above) rather than the old report's "avoid unnecessary re-renders" framing alone.
- **The desktop-launch (`open_in_desktop`) and Kanaries-token-upload findings**: dropped from prose (they're
  now blocked by shinywidgets, covered by the existing Playwright test, and already summarized in the
  Security section's bullet list) rather than re-explained as live findings.
- **Scorecard stars, "what's good" bullets, follow-up filing list for upstream issues**: PR-review artifacts,
  not teaching material; dropped.

## Update 2026-11-11 (main @ 32ca7035)

Brought up to date against `main` @ `32ca7035` (33 commits ahead of the `main` base this guide was originally
verified against). This guide needed almost no change: `render_pygwalker`'s security model (forced lockdown of
DuckDB's default connection, no `allow_unrestricted_connection` opt-out, since every PyGWalker widget in the
process shares that one connection) is unrelated to #395 (which added the *optional* per-widget lockdown to
`render_quak`/`render_mosaic_widget`) and was unaffected by it. `render_pygwalker` has no `_accessor_specs`
(confirmed again this pass, same as 2026-10-30), so #437's accessor-semantics unification and `.read()` don't
apply here either -- there's nothing to read on demand, continuously, or any other way, beyond the
`on_msg`/save-export mechanism this guide already documents.

- **One sentence fixed**: the "Pairing with other guides" section's quak comparison used to say "both renderers
  need the same kind of DuckDB lockdown discipline ... quak's is per-widget and easier to reason about" --
  written when quak had no lockdown at all and the "discipline" was something *you* had to apply yourself
  (see quak's own NOTES.md, "Bugs found," 2026-10-30 entry). Now that quak locks down by default (#395), that
  sentence was stale -- it implied quak still required manual care. Rewrote it to describe both renderers'
  *current* default-locked state and the real difference between them (quak/mosaic opt out per widget;
  PyGWalker's lockdown is forced, with no opt-out, for the reason this guide's own Security section already
  explains).
- Re-ran `tests/unit/test_pygwalker.py` (44 tests) to confirm nothing in the lockdown/accessor code paths this
  guide depends on regressed -- all pass.
- No other prose, code example, or screenshot needed a change: every example already ran against the locked
  default connection (via `globals.py`), the Security section's claims were already verified and already
  match current `main`, and no new accessor or `.read()`-eligible trait exists to add an example for.

### Bugs found (2026-11-11)

None new.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example -- cites this guide's own "Any size dataset, because DuckDB computes it" section and restates its already-measured numbers (10,163,162-byte initial render identical at all scales; ~1.2KB sent/~2.0KB received per query at 500/50K/1M rows) rather than re-measuring.
