# NOTES: Perspective guide

## Versions

- `perspective-python` 5.6.0, `shiny` 1.9.0, `pandas`, `plotly` 6.x, Python 3.12.
- shinywidgets commit: current `main` at time of writing (2026-10-30), after the reactive-accessors pass landed
  (`filter()`, `view_config()` on `render_perspective`; `shinywidgets/_perspective.py`).
- Playwright: Chromium (default headless launch; no WebGL args needed -- Perspective renders fine in plain
  headless mode).
- Partway through this pass, another agent's branch switch in the main checkout made `uv run` there transiently
  fail (mid-edit `pyproject.toml`/`_render_widget.py`). The coordinator pointed later verification runs at an
  isolated worktree (`scratchpad/main-wt`, its own synced venv, detached at `origin/main`) with absolute paths
  back to this guide's directory. Examples 11-13, the gallery apps, and their screenshots were last verified from
  that worktree; everything before that (01-10, 14) was verified in the main checkout before the conflict and not
  re-run, since nothing about their code changed as a result.

## Dataset choice

Per the coordinator's mid-task note preferring real, recognizable datasets for hero/quickstart/gallery material,
every static (non-streaming) example uses `plotly.express.data.gapminder()` (142 countries, 1952-2007
population/GDP/life-expectancy -- ships with `plotly`, already a dependency used elsewhere in this guide) instead
of synthetic sector/trade data. The two inherently-live examples (`05_streaming.py` and both gallery apps) keep
synthetic *values* (there's no live public market feed without an API key) but use real, recognizable stock
tickers (AAPL, MSFT, GOOG, ...) rather than invented ones. `11_linked_shared_table.py`'s "shared table" demo uses
`table.update()` with an upsert (`index="country"`) carrying revised population figures for three real
countries, rather than appending synthetic rows, since gapminder is historical/static and inventing fake new
"countries" would have been a worse fit than a legitimate revise-the-data-in-place scenario.

One side effect worth flagging: switching the pivot example (`02_pivoting.py`) to two gapminder snapshots
(1952 and 2007) made `split_by=["year"]` a genuinely meaningful comparison ("world population then vs. now"),
which is a stronger demonstration of `split_by` than the original synthetic buy/sell data was.

## Verification table

All apps run via `uv run --no-sync shiny run <file> --port <port>` (ports 9320-9339) and screenshotted with
Python Playwright, Chromium, 1280-1600 wide x 500-800 tall, `device_scale_factor=2`. Every screenshot referenced
in `guide.md` was read with the Read tool before being cited.

| File | Ran | Screenshot | Gesture driven | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a (static) | confirms default `settings=True`; 142 countries, 2007 snapshot |
| `examples/02_pivoting.py` | yes | yes | n/a | 1952-vs-2007 population by continent; iterated once to exclude the auto "index" column from the sum |
| `examples/03_plugins.py` | yes | yes | n/a | world population treemap by continent/country; iterated once (Treemap defaulted to sizing by "index" until `columns=["pop"]` was added) |
| `examples/04_expressions.py` | yes | yes | n/a | `gdp_billions` expression checked against real GDP figures (e.g. Afghanistan ≈ $31B, matches reality) |
| `examples/05_streaming.py` | yes | yes | n/a (visual: row count grew during the screenshot wait) | real tickers (AAPL/MSFT/GOOG) instead of fictional sectors |
| `examples/06_filter_accessor.py` | yes | before/after pair | yes -- drag `continent` into Where, commit a value | `filter()` seeded `[]`, then updated to `[['continent', '==', 'Africa']]`; confirms docstring |
| `examples/07_view_config_accessor.py` | yes | before/after pair | yes -- click `gdpPercap` header to sort | `view_config()["sort"]` updated; result (Norway, Kuwait, Singapore) matches real 2007 GDP-per-capita rankings |
| `examples/08_reactive_read_theme.py` | yes | before/after pair | yes -- `el.restore({settings:false})` | surfaced the `theme: None` at first render finding, see Bugs found (docs) |
| `examples/09_update_in_place.py` | yes | before/after pair | yes -- click `input_dark_mode` button | theme flips to Pro Dark; a manually-set sort by `gdpPercap` survives, confirming in-place vs. re-render |
| `examples/10_linked_filtered_summary.py` | yes | before/after pair | yes -- drag `continent` into Group By | total population (6,251,013,179 -- the real 2007 world population) identical before/after grouping, confirming the grand-total-row fix is necessary and correct |
| `examples/11_linked_shared_table.py` | yes | before/after pair | yes -- click "Apply revised population estimates" | read China's population *through the treemap's own `getTable()`* after clicking the button on the datagrid's table; it reflected the revision (1,360,000,000), proving the two widgets share one table, not just matching starting data |
| `examples/12_linked_save_restore.py` | yes | before/after pair | yes -- drag `continent` into Group By, Save, `el.restore({group_by:[]})`, Restore | restore brought back the exact saved pivot |
| `examples/13_linked_crosswidget_chart.py` | yes | before/after pair | yes -- `el.restore({filter:[['continent','==','Asia']]})` | plotly bar chart collapsed from 5 continents to 1 (Asia, ~3.8B), matching the grid's filtered rows |
| `examples/14_layout_sizing.py` | yes | yes | n/a | confirms fill/full_screen/explicit height work with no extra config |
| `gallery/template_live_feed.py` | yes | before/after pair | yes -- click Reset | pivoted Y Bar (by symbol) vs. flat per-trade bars |
| `gallery/showcase_trading_desk.py` | yes | 3 screenshots | yes -- click Pivot radio, click dark-mode button | value boxes recompute from `grid.filter()`; Pivot preset applies via `hold_sync()`; dark mode updates both viewers' themes in place; already used real tickers/sectors, unchanged by the dataset-preference note |

Additionally ran the existing test suites on current `main` as corroborating evidence (not re-derived by me):
`uv run --no-sync pytest tests/playwright/render_perspective tests/playwright/perspective_accessors
tests/playwright/render_perspective_fill tests/playwright/render_perspective_output_height
tests/playwright/render_perspective_widget_height` (10 passed) and
`uv run --no-sync pytest tests/unit/test_perspective.py tests/unit/test_perspective_accessors.py` (15 passed).
These cover: per-session table isolation (the old report's blocker B1 is fixed on main), `update()` streaming
without re-render, two viewers sharing a page, viewer-state round-trip via `el.restore()`, and the `view_config()`
equality-gate on cosmetic vs. structural keys.

## Accessor coverage

- `filter()`: verified with a real gesture (drag-and-drop into the Where field + commit a value).
- `view_config()`: verified with a real gesture (column-header click to sort; separately, grouping via
  drag-and-drop in the linked-view examples).

Both accessors are `kind="state"`, carry no default rate policy, and seed synchronously at attach -- all
confirmed either by the unit tests (`tests/unit/test_perspective_accessors.py`) or by direct inspection of
`shinywidgets/_perspective.py`.

## Bugs found

### shinywidgets

None found on current `main`. The old report's two blockers are both resolved:
- **B1 (cross-session table exposure)**: fixed. `_as_widget.py::perspective_widget()` now builds a private
  `Server().new_local_client().table(data)` for any non-`Table` input, and
  `tests/playwright/render_perspective/test_render_perspective.py::test_perspective_dataframe_tables_are_private_to_each_session`
  passes.
- **B2 (docstring recommending `.widget.replace()`)**: the current docstring already documents the limitation
  accurately (`.widget.replace()` needs records/dict/Arrow bytes, not a DataFrame) and recommends
  `clear()` + `update(df)` instead. Still an upstream bug (see below), but the docs are now correct.

### Upstream (perspective-python 5.6.0)

- **`Table.replace()` rejects pandas, polars, and pyarrow inputs** (`ValueError: Unknown input type ...`);
  only records, a dict of columns, or Arrow IPC bytes work, even though `update()` accepts all of them.
  Reproduced directly against `perspective.Table`, no shinywidgets involved. Long-standing limitation (also
  reported by the old report against an earlier branch).
- **Grouped `table.view()` results include an unlabeled grand-total row** (`__ROW_PATH__ == []`). Not a bug
  exactly -- it's documented pivot-table behavior -- but easy to get wrong when replaying `view_config()` from
  Python, since naively summing a grouped view's column double-counts the total. New finding from this pass;
  worth calling out because the accessor's self-service pattern (`table.view(**view_config())`) makes it easy to
  hit. Verified with the real 2007 world population: grouped sum of all rows would read ~2x the actual total.
- **Setting `columns_config` from Python replaces the dict; restoring it from the browser merges it per column**,
  and there is no way to clear an existing column's config via `restore(columns_config={})`. Matches the old
  report's finding (S4 nit), reproduced independently here against the current `perspective-python` release.
- **The Datagrid's cell-edit mode requires a toolbar/edit-mode toggle that doesn't render in the current
  `perspective-anywidget` bundle.** I tried to replace `11_linked_shared_table.py`'s synced-viewer demo with a
  live cell-edit gesture (double-click a cell, type a new value) instead of a Python-side `table.update()`
  button, since that would have been an even more "real UI" gesture. Reverse-engineering the minified JS showed
  cell edits require `_edit_mode === "EDIT"`, toggled by a `<perspective-viewer-datagrid-toolbar>` element's
  `#edit_mode` button -- but that toolbar element never appears in the rendered shadow DOM in this build, with or
  without `index=` set on the table, so double-click-to-edit never activates. I didn't chase this further (no
  config option surfaced it, and the old report's "the grid is editable" claim may describe a different
  perspective version / build). Not confirmed as a shinywidgets-caused regression; flagging as unverified rather
  than reporting it as a bug. The table-update-via-button approach (verified, see above) demonstrates the same
  "shared table" concept without depending on this.

### Docs (on current main, found per the coordinator's "docstrings can be wrong" instruction)

- `render_perspective`'s docstring is otherwise accurate, but it doesn't mention that `reactive_read(widget,
  "theme")` (or any cosmetic trait) can read `None` immediately after a render, before the browser's first sync.
  I verified this directly (`examples/08_reactive_read_theme.py`'s first screenshot prints `theme: None`). This
  is worth a one-line addition to the docstring, since it's an easy trap for anyone reading cosmetic traits
  outside the accessors.
- Nothing else checked against the docstring turned out to be wrong: the per-session-server guidance, the
  `.widget.replace()` limitation, the pandas-index-column note, and the `view_config()`/`filter()` accessor
  descriptions all matched observed behavior exactly.

## Judgment calls (flag for the maintainer)

1. **Gallery docstring headers display as page text in Shiny Express -- I used `#`-comment headers instead.**
   (The coordinator's mid-task note independently confirmed this and updated BRIEF.md; recorded here since I'd
   already hit and fixed it.) Shiny Express treats every top-level expression statement (including a bare module
   docstring) as something to render via its `displayhook`, so a real triple-quoted docstring prints itself as a
   paragraph at the top of the rendered app (confirmed: hit this on the first run of `template_live_feed.py`,
   screenshot showed the whole header paragraph above the controls). Both gallery files use a `#`-comment header
   instead, with a one-line note explaining why.
2. **The settings-panel filter's value field is a combobox that doesn't always commit the typed text.** Across
   several gestures (`examples/06`, `examples/13`, and the pre-existing
   `tests/playwright/perspective_accessors` test), typing a value and pressing Enter sometimes commits the
   combobox's highlighted (first-alphabetical-match) option instead of the literal text, and sometimes commits
   the literal text verbatim if it matches no existing category (e.g. typing "Tech" against a continent column
   produces a filter for literal "Tech", matching zero rows). For `examples/13`, I switched the gesture to
   `el.restore({filter: [...]})` -- the same call the settings UI makes internally -- for a deterministic result;
   `examples/06` keeps the drag-and-type gesture and reports whatever it actually commits (Africa), rather than
   asserting a value I couldn't reliably reproduce. Flagged as a Gotcha in `guide.md` for anyone else scripting
   this UI.
3. **No separate example file for "Rate limiting."** Neither accessor declares a default rate policy, and I
   couldn't construct a realistic Perspective scenario where a user would want to rate-limit `reactive_read()` on
   a cosmetic trait (the traits that change rapidly, like `filter`/`sort`/`group_by`, are already covered by the
   accessors, which aren't rate-limited by design). I described the kwarg in prose instead of inventing a
   contrived snippet, per "never pad."
4. **`11_linked_shared_table.py`'s interactive gesture is a Python-side button, not a direct-manipulation
   gesture in one viewer.** I'd have preferred demonstrating "shared table" via an edit made directly in the
   browser (cell edit in the datagrid reflected in the treemap), but that's blocked by the toolbar issue above.
   The button-triggered `table.update()` still proves the two widgets share one table (verified by reading the
   revised value back through the *other* viewer's own connection), just via a Python-initiated change rather
   than a pure-browser one.

## Editor's notes for the website

- **Strongest screenshots**: `img/gallery_showcase_dark.webp` (dark-mode pivoted blotter + P&L treemap, used as
  the hero) and `img/plugins_treemap.webp` (the real world-population treemap -- immediately recognizable, a good
  candidate if the page needs just one "what you can build" image). The `filtered_summary_before/after.webp` pair
  clearly shows the grand-total-row behavior paying off with a real, checkable number (6.25B people).
- **Candidates to cut for a shorter page**: the "Beyond the accessors: reactive_read" subsection and its
  screenshot pair are the least essential -- the finding (cosmetic traits can read `None`) is valuable as a
  Gotchas bullet even without the dedicated example/screenshot.
- **`examples/13_linked_crosswidget_chart.py`** is the one cross-widget pairing in this guide (pairs with:
  plotly). It's simple on the plotly side by design, per the brief's "keep the other widget simple" instruction.

## What I dropped from the old report and why

- **Weight/memory measurements (ESM bundle size, browser heap growth, per-visit server RSS)**: out of scope for
  a teaching guide; these are performance characteristics of anywidget/shinywidgets in general (the old report
  says as much -- "this affects every large anywidget, not just Perspective"), not something a Perspective user
  decides based on. Mentioned only briefly in Gotchas as "budget for it independently."
- **The scorecard and PR-review verdict**: this guide is written against the released, merged behavior, not a
  pending PR, so a merge recommendation doesn't apply.
- **The `customElements.define` monkeypatch discussion**: an implementation detail of how shinywidgets loads
  Perspective's JS, invisible to a user following this guide; not relevant to "what you can build."
- **Per-visit memory leak measurements**: upstream, long-standing, not something this guide's reader can act on
  beyond the one-line budget note I kept.

## Update 2026-11-11 (main @ 32ca7035)

### What changed and why

- **Accessor reference table reformatted** to the update brief's required columns (`returns | before any
  interaction | across re-render | default rate policy`), replacing the pre-redesign `fires when | None/empty
  means | default rate policy` columns.
- **`filter()`/`view_config()` re-render semantics made explicit and verified.** Checked
  `shinywidgets/_perspective.py`: both `attach_filter` and `attach_view_config` call `emit(...)` synchronously at
  attach, reading straight off the new widget's current trait values, every render -- so both accessors are
  **re-seeded** from the new viewer, not kept from the old one. (No new browser verification needed for this
  specifically -- it follows directly from the attach functions always emitting at render, the same mechanism
  already exercised by every other accessor example in this guide.)
- **`examples/08_reactive_read_theme.py` converted from `reactive_read(widget, "theme")` to
  `grid.read("theme")`**, per #437's new `.read()` API and the update brief's narrative (tier 2: `.read()`
  replaces `reactive_read()` as the taught fallback for the output's own traits, everywhere a renderer output
  exists). Re-verified with a real gesture (closing the settings panel via `#settings_close_button`):
  `grid.read("theme")` reads `None` immediately after render, then `'Pro Light'` once the browser's first sync
  lands, and `grid.read("settings")` flips `True` -> `False` on close -- identical to the old
  `reactive_read()`-based behavior, confirming the conversion preserves the exact claim being taught.
  Screenshots replaced (`img/reactive_read_before.webp`, `img/reactive_read_after.webp`). Updated the "Beyond the
  accessors" section heading/prose and the matching Gotchas bullet to match (both now say `grid.read("theme")`,
  with `reactive_read()` mentioned as the equivalent it falls through to, not the headline API).
- **New example, `examples/15_export_filtered.py`** ("Read on demand: export filtered rows"): a
  `@render.download_button` handler reads `grid.filter()` cold, at click time, replays it against the table with
  `table.view(filter=...)`, and exports the result as CSV -- with no other reader of `filter()` anywhere in the
  app. Demonstrates the redesign's headline read-on-demand capability. Added as a new subsection in "Reacting to
  user interaction", between `filter()` and `view_config()`.

### Re-verification (unpatched main @ 32ca7035, perspective-python 5.6.1)

| File | Gesture | Confirmed |
|---|---|---|
| `examples/08_reactive_read_theme.py` (rewritten) | loaded page, then clicked `#settings_close_button` | `theme: None` immediately after render -> `theme: 'Pro Light'` after first sync; `settings panel open: True` -> `False` |
| `examples/15_export_filtered.py` (new) | `el.restore({filter: [['continent', '==', 'Africa']]})` (deterministic equivalent of the drag-into-Where gesture, per judgment call 2 below), then clicked download | grid showed "52 (142) / 7" rows; downloaded CSV had exactly 53 lines (52 African countries + header), all with `continent == Africa` |

Perspective-python resolved to 5.6.1 in this pass's worktree venv (the 2026-10-30 NOTES recorded 5.6.0); this is
an unrelated dependency bump, not part of the 33-commit shinywidgets update, and nothing in this guide's content
depends on the difference.

Did not re-run examples 01-07, 09-14, or the gallery apps: `shinywidgets/_perspective.py` (the accessor bridge)
is otherwise untouched by the 33-commit update, and none of those files' claims needed correction. Their
2026-10-30 verification status in the table above this section stands.

### New bugs found this pass

None.

### Front-matter

`accessors:` list unchanged (`[filter, view_config]`).

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example. Described Perspective's actual architecture (Arrow once into the browser's WASM engine, then zero-round-trip local queries; table.update() for incremental appends) rather than forcing it into the "only send what's visible" bucket the design doc's table uses -- noted explicitly that the fit is loose, since the initial load ships the whole table, not just what's visible.
